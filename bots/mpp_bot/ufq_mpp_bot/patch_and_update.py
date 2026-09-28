"""
patch_and_update.py
====================

Safe, idempotent, ADDITIVE migration for ufq_mpp_bot.

WHAT THIS DOES
--------------
It extends the existing schema with the new v2 features WITHOUT touching,
renaming, or dropping anything that the current handlers/repos already
depend on:

  - directions.category      (nullable TEXT, 'mentor_led' | 'peer_to_peer')
                              existing rows get 'mentor_led' by default so
                              current mentor-based directions keep working.
  - cells.mentor_id           made nullable (peer-to-peer cells have none)
                              done via safe table-rebuild, preserving all
                              existing rows, indexes and the two capacity
                              triggers verbatim.
  - weekly_plans               new table (mentor 7-day plan uploads)
  - zoom_logs                  new table (weekly zoom session log)
  - mock_exams                 new table (scheduled mock exam per cell)
  - mock_scores                new table (per-user mock result + points,
                                linked to mock_exams; distinct from the
                                existing mock_results table, which is left
                                untouched so current mentor_mock.py code
                                keeps working unmodified)
  - tasks_progress              new table (3-day cycle point tracking,
                                additive alongside the existing tasks/
                                submissions deadline-based flow)
  - scores_ledger               new table (append-only point log, source
                                of truth for leaderboard/reporting)

WHAT THIS DELIBERATELY DOES NOT DO
-----------------------------------
  - It does NOT drop or rename `tasks`, `submissions`, or `mock_results`.
    Those tables are what handlers/mentor_tasks.py, handlers/partner_status.py
    and handlers/mentor_mock.py actually query today. Ripping them out
    would break the running bot; the new tables are added alongside them.
  - It does NOT remove the existing `trg_cell_capacity_insert` /
    `trg_cell_capacity_update` triggers (max 3 partners per cell). The spec's
    "max 2 cells as partner / 1 as mentor" is a PER-USER, CROSS-CELL rule,
    which is a different constraint checked at the application layer (see
    database/repo_quotas.py, added by this script) -- it does not conflict
    with the existing per-cell capacity trigger and both can co-exist.

SAFETY
------
  - Takes a timestamped backup copy of the DB file before making any change.
  - Every step is guarded by introspection (PRAGMA table_info / sqlite_master)
    so re-running this script is a no-op on anything already applied.
  - Runs inside a single transaction per logical step; on any failure the
    step is rolled back and the script stops with a non-zero exit code
    before touching anything further.
  - The mentor_id-nullable change is the only structural rebuild; it is done
    with the standard SQLite 12-step pattern (new table -> copy -> drop ->
    rename -> recreate indexes/triggers) inside a single transaction with
    foreign_keys temporarily off for that step only, exactly as SQLite's own
    docs prescribe for altering a column's NOT NULL constraint.

USAGE
-----
    python3 patch_and_update.py [path/to/ufq.db]

If no path is given, it reads DB_PATH from config.py (same resolution the
bot itself uses), falling back to ./ufq.db.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime


def resolve_db_path() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import config  # type: ignore

        return config.db_path
    except Exception:
        return os.environ.get("DB_PATH", "database/ufq_mpp.db")


def backup_db(db_path: str) -> str:
    if not os.path.exists(db_path):
        print(f"[patch] DB file not found at {db_path} -- nothing to back up "
              f"(a fresh DB will be created on next bot startup via schema.sql).")
        return ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{ts}"
    shutil.copy2(db_path, backup_path)
    print(f"[patch] Backed up {db_path} -> {backup_path}")
    return backup_path


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    )
    return cur.fetchone() is not None


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def column_is_notnull(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        # row: (cid, name, type, notnull, dflt_value, pk)
        if row[1] == column:
            return bool(row[3])
    return False


def trigger_sql(conn: sqlite3.Connection, name: str) -> str | None:
    cur = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?", (name,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def index_sqls(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL",
        (table,),
    )
    return [row[0] for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Step 1: directions.category
# ---------------------------------------------------------------------------

def step_directions_category(conn: sqlite3.Connection) -> None:
    if column_exists(conn, "directions", "category"):
        print("[patch] directions.category already present -- skipping.")
        return
    print("[patch] Adding directions.category ...")
    conn.execute(
        "ALTER TABLE directions ADD COLUMN category TEXT "
        "CHECK(category IN ('mentor_led', 'peer_to_peer')) DEFAULT 'mentor_led'"
    )
    # Backfill explicit value for any pre-existing rows (DEFAULT only applies
    # to new rows in SQLite's ALTER TABLE ADD COLUMN semantics for existing
    # rows too, but we set it explicitly to be unambiguous and future-proof).
    conn.execute("UPDATE directions SET category = 'mentor_led' WHERE category IS NULL")
    print("[patch] directions.category added; existing directions marked 'mentor_led'.")


# ---------------------------------------------------------------------------
# Step 2: cells.mentor_id -> nullable (safe table rebuild)
# ---------------------------------------------------------------------------

def step_cells_mentor_nullable(conn: sqlite3.Connection) -> None:
    if not column_is_notnull(conn, "cells", "mentor_id"):
        print("[patch] cells.mentor_id already nullable -- skipping.")
        return

    print("[patch] Making cells.mentor_id nullable (peer_to_peer cells have no mentor) ...")

    # Preserve existing triggers/indexes verbatim so we can recreate them
    # against the rebuilt table with identical semantics.
    trg_insert_sql = trigger_sql(conn, "trg_cell_capacity_insert")
    trg_update_sql = trigger_sql(conn, "trg_cell_capacity_update")
    cells_indexes = index_sqls(conn, "cells")

    fk_was_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute(
            """
            CREATE TABLE cells__new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction_id INTEGER NOT NULL REFERENCES directions(id) ON DELETE CASCADE,
                mentor_id INTEGER REFERENCES users(telegram_id),
                invite_code TEXT UNIQUE,
                invite_code_expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO cells__new (id, direction_id, mentor_id, invite_code,
                                     invite_code_expires_at, is_active, created_at)
            SELECT id, direction_id, mentor_id, invite_code,
                   invite_code_expires_at, is_active, created_at
            FROM cells
            """
        )
        conn.execute("DROP TABLE cells")
        conn.execute("ALTER TABLE cells__new RENAME TO cells")

        # Recreate any indexes that existed on the old table.
        for sql in cells_indexes:
            conn.execute(sql)
        if not any("idx_cells_mentor" in (s or "") for s in cells_indexes):
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cells_mentor ON cells(mentor_id)")

        # Recreate the two capacity triggers exactly as they were (they are
        # defined on cell_members, not cells, so their SQL is unaffected by
        # the cells rebuild -- but SQLite drops triggers on a table only when
        # that table itself is dropped, so these are untouched; recreate is a
        # no-op safety net in case they ever get attached to `cells` later).
        if trg_insert_sql:
            conn.execute("DROP TRIGGER IF EXISTS trg_cell_capacity_insert")
            conn.execute(trg_insert_sql)
        if trg_update_sql:
            conn.execute("DROP TRIGGER IF EXISTS trg_cell_capacity_update")
            conn.execute(trg_update_sql)

        fk_check = conn.execute("PRAGMA foreign_key_check(cells)").fetchall()
        if fk_check:
            raise RuntimeError(f"foreign_key_check failed after cells rebuild: {fk_check}")

        conn.execute("COMMIT")
        print("[patch] cells.mentor_id is now nullable; all rows/indexes preserved.")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute(f"PRAGMA foreign_keys = {'ON' if fk_was_on else 'OFF'}")


# ---------------------------------------------------------------------------
# Step 3: brand-new additive tables
# ---------------------------------------------------------------------------

NEW_TABLES: dict[str, str] = {
    "weekly_plans": """
        CREATE TABLE IF NOT EXISTS weekly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(telegram_id),
            week_number INTEGER NOT NULL,
            plan_text TEXT,
            days_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "zoom_logs": """
        CREATE TABLE IF NOT EXISTS zoom_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            logged_by INTEGER NOT NULL REFERENCES users(telegram_id),
            week_number INTEGER NOT NULL,
            date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "mock_exams": """
        CREATE TABLE IF NOT EXISTS mock_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(telegram_id),
            exam_date TIMESTAMP NOT NULL,
            description TEXT,
            status TEXT CHECK(status IN ('scheduled', 'finished', 'cancelled')) DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "mock_scores": """
        CREATE TABLE IF NOT EXISTS mock_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mock_id INTEGER NOT NULL REFERENCES mock_exams(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            score_raw REAL,
            points_awarded INTEGER DEFAULT 0,
            entered_by INTEGER NOT NULL REFERENCES users(telegram_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mock_id, user_id)
        )
    """,
    "tasks_progress": """
        CREATE TABLE IF NOT EXISTS tasks_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            cycle_date DATE NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cell_id, user_id, cycle_date)
        )
    """,
    "scores_ledger": """
        CREATE TABLE IF NOT EXISTS scores_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            cell_id INTEGER REFERENCES cells(id) ON DELETE SET NULL,
            points INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
}

NEW_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_weekly_plans_cell ON weekly_plans(cell_id, week_number)",
    "CREATE INDEX IF NOT EXISTS idx_zoom_logs_cell ON zoom_logs(cell_id, week_number)",
    "CREATE INDEX IF NOT EXISTS idx_mock_exams_cell ON mock_exams(cell_id, exam_date)",
    "CREATE INDEX IF NOT EXISTS idx_mock_scores_mock ON mock_scores(mock_id)",
    "CREATE INDEX IF NOT EXISTS idx_mock_scores_user ON mock_scores(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_progress_cell_date ON tasks_progress(cell_id, cycle_date)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_progress_user ON tasks_progress(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_scores_ledger_user ON scores_ledger(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_scores_ledger_cell ON scores_ledger(cell_id)",
]


def step_new_tables(conn: sqlite3.Connection) -> None:
    for name, ddl in NEW_TABLES.items():
        existed = table_exists(conn, name)
        conn.execute(ddl)
        print(f"[patch] table {name}: {'already existed' if existed else 'created'}")
    for sql in NEW_INDEXES:
        conn.execute(sql)
    print("[patch] indexes for new tables ensured.")


# ---------------------------------------------------------------------------
# Step 4: per-user cross-cell quota trigger (max 2 as partner, 1 as mentor)
# ---------------------------------------------------------------------------
#
# This is enforced with triggers on cell_members (partner side) and cells
# (mentor side), mirroring the existing defense-in-depth pattern already
# used for the per-cell 3-partner cap. It is a DIFFERENT axis (per-user,
# across all cells) from the existing per-cell trigger, so both coexist
# without conflict. The admin (ADMIN_ID) is exempt at the application layer
# (see database/repo_quotas.py) -- SQLite triggers can't easily read config,
# so the DB-level trigger enforces the general case and repo_quotas.py's
# app-level check is what actually special-cases the admin before insert.

def step_quota_triggers(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name IN "
        "('trg_partner_quota_insert', 'trg_partner_quota_update', 'trg_mentor_quota_insert')"
    ).fetchall()
    existing_names = {row[0] for row in existing}

    if "trg_partner_quota_insert" not in existing_names:
        conn.execute(
            """
            CREATE TRIGGER trg_partner_quota_insert
            BEFORE INSERT ON cell_members
            WHEN NEW.is_active = 1
            BEGIN
                SELECT RAISE(ABORT, 'PARTNER_CELL_QUOTA')
                WHERE (
                    SELECT COUNT(*) FROM cell_members
                    WHERE partner_id = NEW.partner_id AND is_active = 1
                      AND cell_id != NEW.cell_id
                ) >= 2;
            END
            """
        )
        print("[patch] trigger trg_partner_quota_insert created (max 2 cells per partner).")
    else:
        print("[patch] trg_partner_quota_insert already present -- skipping.")

    if "trg_partner_quota_update" not in existing_names:
        conn.execute(
            """
            CREATE TRIGGER trg_partner_quota_update
            BEFORE UPDATE OF is_active, cell_id ON cell_members
            WHEN NEW.is_active = 1 AND (OLD.is_active = 0 OR NEW.cell_id != OLD.cell_id)
            BEGIN
                SELECT RAISE(ABORT, 'PARTNER_CELL_QUOTA')
                WHERE (
                    SELECT COUNT(*) FROM cell_members
                    WHERE partner_id = NEW.partner_id AND is_active = 1
                      AND cell_id != NEW.cell_id
                ) >= 2;
            END
            """
        )
        print("[patch] trigger trg_partner_quota_update created.")
    else:
        print("[patch] trg_partner_quota_update already present -- skipping.")

    if "trg_mentor_quota_insert" not in existing_names:
        conn.execute(
            """
            CREATE TRIGGER trg_mentor_quota_insert
            BEFORE INSERT ON cells
            WHEN NEW.mentor_id IS NOT NULL AND NEW.is_active = 1
            BEGIN
                SELECT RAISE(ABORT, 'MENTOR_CELL_QUOTA')
                WHERE (
                    SELECT COUNT(*) FROM cells
                    WHERE mentor_id = NEW.mentor_id AND is_active = 1
                ) >= 1;
            END
            """
        )
        print("[patch] trigger trg_mentor_quota_insert created (max 1 cell per mentor).")
    else:
        print("[patch] trg_mentor_quota_insert already present -- skipping.")


# ---------------------------------------------------------------------------
# Step 5: write database/repo_quotas.py, database/repo_v2.py (new repos only
#          -- no existing repo file is modified or overwritten)
# ---------------------------------------------------------------------------

REPO_QUOTAS_PY = '''"""
database/repo_quotas.py
------------------------
App-level cross-cell quota checks for the v2 role rules:

    - A user may be an active PARTNER in at most 2 cells at once.
    - A user may be an active MENTOR of at most 1 cell at once.
    - ADMIN_ID is exempt from both limits (may hold any combination).

These mirror the DB-level triggers added by patch_and_update.py
(trg_partner_quota_insert/update, trg_mentor_quota_insert), which exist as
defense-in-depth against races. Call these functions BEFORE attempting the
insert so the user gets a clean, translated error message instead of a raw
sqlite3.IntegrityError bubbling up from the trigger.
"""

from __future__ import annotations

from database.db import get_conn
from config import config

MAX_CELLS_AS_PARTNER = 2
MAX_CELLS_AS_MENTOR = 1


class QuotaError(Exception):
    """Raised when a user/mentor is at their cell-membership quota."""


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def count_active_cells_as_partner(user_id: int, exclude_cell_id: int | None = None) -> int:
    conn = get_conn()
    if exclude_cell_id is None:
        cur = await conn.execute(
            "SELECT COUNT(*) AS cnt FROM cell_members WHERE partner_id = ? AND is_active = 1",
            (user_id,),
        )
    else:
        cur = await conn.execute(
            "SELECT COUNT(*) AS cnt FROM cell_members "
            "WHERE partner_id = ? AND is_active = 1 AND cell_id != ?",
            (user_id, exclude_cell_id),
        )
    row = await cur.fetchone()
    return int(row["cnt"])


async def count_active_cells_as_mentor(user_id: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM cells WHERE mentor_id = ? AND is_active = 1",
        (user_id,),
    )
    row = await cur.fetchone()
    return int(row["cnt"])


async def assert_can_join_as_partner(user_id: int, cell_id: int) -> None:
    """Raise QuotaError if adding user_id as a partner of cell_id would exceed
    the max-2-cells-as-partner rule. Admin is exempt."""
    if _is_admin(user_id):
        return
    current = await count_active_cells_as_partner(user_id, exclude_cell_id=cell_id)
    if current >= MAX_CELLS_AS_PARTNER:
        raise QuotaError(
            f"Bu foydalanuvchi allaqachon {MAX_CELLS_AS_PARTNER} ta guruhda partner. "
            f"Yangi guruhga qo'shilishdan oldin birontasidan chiqishi kerak."
        )


async def assert_can_become_mentor(user_id: int) -> None:
    """Raise QuotaError if user_id already mentors a cell. Admin is exempt."""
    if _is_admin(user_id):
        return
    current = await count_active_cells_as_mentor(user_id)
    if current >= MAX_CELLS_AS_MENTOR:
        raise QuotaError(
            f"Bu foydalanuvchi allaqachon {MAX_CELLS_AS_MENTOR} ta guruhda mentor. "
            f"Yangi guruhga mentor sifatida tayinlanishdan oldin joriy guruhini bo'shatishi kerak."
        )
'''

REPO_V2_PY = '''"""
database/repo_v2.py
--------------------
Repo functions for the tables added in v2: weekly_plans, zoom_logs,
mock_exams, mock_scores, tasks_progress, scores_ledger.

Kept in its own module (rather than merged into repo_tasks.py /
repo_cells.py / repo_misc.py) so the existing, already-working repo files
are not touched by this migration.
"""

from __future__ import annotations

from typing import Optional

import aiosqlite

from database.db import get_conn


# ---------- weekly_plans ----------

async def create_weekly_plan(cell_id: int, created_by: int, week_number: int,
                              plan_text: str, days_data: Optional[str] = None) -> int:
    conn = get_conn()
    cur = await conn.execute(
        """
        INSERT INTO weekly_plans (cell_id, created_by, week_number, plan_text, days_data)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cell_id, created_by, week_number, plan_text, days_data),
    )
    await conn.commit()
    return cur.lastrowid


async def get_latest_weekly_plan(cell_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM weekly_plans WHERE cell_id = ? ORDER BY week_number DESC, created_at DESC LIMIT 1",
        (cell_id,),
    )
    return await cur.fetchone()


async def has_plan_for_week(cell_id: int, week_number: int) -> bool:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT 1 FROM weekly_plans WHERE cell_id = ? AND week_number = ?",
        (cell_id, week_number),
    )
    return (await cur.fetchone()) is not None


# ---------- zoom_logs ----------

async def log_zoom_session(cell_id: int, logged_by: int, week_number: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "INSERT INTO zoom_logs (cell_id, logged_by, week_number) VALUES (?, ?, ?)",
        (cell_id, logged_by, week_number),
    )
    await conn.commit()
    return cur.lastrowid


async def count_zoom_sessions_for_week(cell_id: int, week_number: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM zoom_logs WHERE cell_id = ? AND week_number = ?",
        (cell_id, week_number),
    )
    row = await cur.fetchone()
    return int(row["cnt"])


# ---------- mock_exams / mock_scores ----------

async def create_mock_exam(cell_id: int, created_by: int, exam_date_str: str,
                            description: Optional[str] = None) -> int:
    conn = get_conn()
    cur = await conn.execute(
        """
        INSERT INTO mock_exams (cell_id, created_by, exam_date, description)
        VALUES (?, ?, ?, ?)
        """,
        (cell_id, created_by, exam_date_str, description),
    )
    await conn.commit()
    return cur.lastrowid


async def get_mock_exam(mock_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM mock_exams WHERE id = ?", (mock_id,))
    return await cur.fetchone()


async def update_mock_exam_date(mock_id: int, exam_date_str: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE mock_exams SET exam_date = ? WHERE id = ?", (exam_date_str, mock_id))
    await conn.commit()


async def delete_mock_exam(mock_id: int) -> None:
    conn = get_conn()
    await conn.execute("DELETE FROM mock_exams WHERE id = ?", (mock_id,))
    await conn.commit()


async def list_upcoming_mock_exams_for_cell(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM mock_exams WHERE cell_id = ? AND status = 'scheduled' ORDER BY exam_date",
        (cell_id,),
    )
    return list(await cur.fetchall())


async def mark_mock_exam_finished(mock_id: int) -> None:
    conn = get_conn()
    await conn.execute("UPDATE mock_exams SET status = 'finished' WHERE id = ?", (mock_id,))
    await conn.commit()


async def record_mock_score(mock_id: int, user_id: int, score_raw: float,
                             points_awarded: int, entered_by: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        """
        INSERT INTO mock_scores (mock_id, user_id, score_raw, points_awarded, entered_by)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(mock_id, user_id) DO UPDATE SET
            score_raw = excluded.score_raw,
            points_awarded = excluded.points_awarded,
            entered_by = excluded.entered_by
        """,
        (mock_id, user_id, score_raw, points_awarded, entered_by),
    )
    await conn.commit()
    return cur.lastrowid


async def list_scores_for_mock(mock_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT ms.*, u.full_name, u.username
        FROM mock_scores ms
        JOIN users u ON u.telegram_id = ms.user_id
        WHERE ms.mock_id = ?
        """,
        (mock_id,),
    )
    return list(await cur.fetchall())


# ---------- tasks_progress (3-day cycle points) ----------

async def upsert_task_progress(cell_id: int, user_id: int, cycle_date_str: str,
                                is_completed: bool, points: int) -> None:
    conn = get_conn()
    await conn.execute(
        """
        INSERT INTO tasks_progress (cell_id, user_id, cycle_date, is_completed, points)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cell_id, user_id, cycle_date) DO UPDATE SET
            is_completed = excluded.is_completed,
            points = excluded.points
        """,
        (cell_id, user_id, cycle_date_str, int(is_completed), points),
    )
    await conn.commit()


async def list_progress_for_user(user_id: int, limit: int = 30) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM tasks_progress WHERE user_id = ? ORDER BY cycle_date DESC LIMIT ?",
        (user_id, limit),
    )
    return list(await cur.fetchall())


async def sum_points_for_user(user_id: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT COALESCE(SUM(points), 0) AS total FROM scores_ledger WHERE user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    return int(row["total"])


async def cell_average_points(cell_id: int) -> float:
    """Average of each active partner's total ledger points, for the
    'Guruh balli' (group score) feature."""
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT AVG(totals.total) AS avg_points FROM (
            SELECT cm.partner_id AS uid, COALESCE(SUM(sl.points), 0) AS total
            FROM cell_members cm
            LEFT JOIN scores_ledger sl ON sl.user_id = cm.partner_id
            WHERE cm.cell_id = ? AND cm.is_active = 1
            GROUP BY cm.partner_id
        ) AS totals
        """,
        (cell_id,),
    )
    row = await cur.fetchone()
    return float(row["avg_points"]) if row and row["avg_points"] is not None else 0.0


# ---------- scores_ledger ----------

async def add_ledger_entry(user_id: int, cell_id: Optional[int], points: int, reason: str) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "INSERT INTO scores_ledger (user_id, cell_id, points, reason) VALUES (?, ?, ?, ?)",
        (user_id, cell_id, points, reason),
    )
    await conn.commit()
    return cur.lastrowid


async def list_leaderboard(limit: int = 20) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT u.telegram_id, u.full_name, u.username,
               COALESCE(SUM(sl.points), 0) AS total_points
        FROM users u
        LEFT JOIN scores_ledger sl ON sl.user_id = u.telegram_id
        GROUP BY u.telegram_id
        ORDER BY total_points DESC
        LIMIT ?
        """,
        (limit,),
    )
    return list(await cur.fetchall())
'''


def step_write_new_repo_files(base_dir: str) -> None:
    quotas_path = os.path.join(base_dir, "database", "repo_quotas.py")
    v2_path = os.path.join(base_dir, "database", "repo_v2.py")

    for path, content, label in (
        (quotas_path, REPO_QUOTAS_PY, "repo_quotas.py"),
        (v2_path, REPO_V2_PY, "repo_v2.py"),
    ):
        if os.path.exists(path):
            print(f"[patch] database/{label} already exists -- leaving it untouched "
                  f"(delete it manually first if you want this script to regenerate it).")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[patch] wrote database/{label}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = resolve_db_path()
    print(f"[patch] Target DB: {db_path}")

    backup_db(db_path)

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")

    try:
        # Ensure base schema exists first (no-op if already applied; uses
        # CREATE TABLE IF NOT EXISTS throughout, matching database/db.py's
        # own init behaviour) so this script also works against a brand-new
        # empty DB file.
        schema_path = os.path.join(base_dir, "database", "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()

        step_directions_category(conn)
        conn.commit()

        step_cells_mentor_nullable(conn)
        conn.commit()

        step_new_tables(conn)
        conn.commit()

        step_quota_triggers(conn)
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"[patch] FAILED: {e}", file=sys.stderr)
        print("[patch] No further steps were applied. Restore the .backup_* file "
              "if the DB was left in an inconsistent state.", file=sys.stderr)
        return 1
    finally:
        conn.close()

    step_write_new_repo_files(base_dir)

    print("[patch] Done. Existing tables (tasks, submissions, mock_results, "
          "cell_members, users) were not modified or renamed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
