from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

from config import config

_connection: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Create the DB file (if needed), apply schema and pragmas. Call once at startup."""
    global _connection
    os.makedirs(os.path.dirname(config.db_path) or ".", exist_ok=True)
    _connection = await aiosqlite.connect(config.db_path)
    _connection.row_factory = aiosqlite.Row
    await _connection.execute("PRAGMA journal_mode = WAL;")
    await _connection.execute("PRAGMA foreign_keys = ON;")
    await _connection.execute("PRAGMA busy_timeout = 5000;")
    with open(config.schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    await _connection.executescript(schema_sql)
    await _connection.commit()

    await _ensure_v2_schema()


async def _ensure_v2_schema() -> None:
    """Idempotently ensure everything patch_and_update.py adds (directions
    .category, cells.mentor_id nullable, the v2 tables, and the quota
    triggers) exists, so the bot works correctly on startup even if that
    script was never run manually against this DB file."""
    conn = get_conn()

    # directions.category
    cur = await conn.execute("PRAGMA table_info(directions)")
    columns = [row[1] for row in await cur.fetchall()]
    if "category" not in columns:
        await conn.execute(
            "ALTER TABLE directions ADD COLUMN category TEXT "
            "CHECK(category IN ('mentor_led', 'peer_to_peer')) DEFAULT 'mentor_led'"
        )
        await conn.execute("UPDATE directions SET category = 'mentor_led' WHERE category IS NULL")
        await conn.commit()

    # cells.mentor_id -> nullable (peer_to_peer cells have no mentor)
    cur = await conn.execute("PRAGMA table_info(cells)")
    cells_info = await cur.fetchall()
    mentor_notnull = any(row[1] == "mentor_id" and row[3] for row in cells_info)
    if mentor_notnull:
        cur = await conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'trg_cell_capacity_insert'"
        )
        row = await cur.fetchone()
        trg_insert_sql = row[0] if row else None
        cur = await conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'trg_cell_capacity_update'"
        )
        row = await cur.fetchone()
        trg_update_sql = row[0] if row else None
        cur = await conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'cells' AND sql IS NOT NULL"
        )
        cells_indexes = [r[0] for r in await cur.fetchall()]

        await conn.execute("PRAGMA foreign_keys = OFF")
        await conn.execute(
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
        await conn.execute(
            """
            INSERT INTO cells__new (id, direction_id, mentor_id, invite_code,
                                     invite_code_expires_at, is_active, created_at)
            SELECT id, direction_id, mentor_id, invite_code,
                   invite_code_expires_at, is_active, created_at
            FROM cells
            """
        )
        await conn.execute("DROP TABLE cells")
        await conn.execute("ALTER TABLE cells__new RENAME TO cells")
        for sql in cells_indexes:
            await conn.execute(sql)
        if not any("idx_cells_mentor" in (s or "") for s in cells_indexes):
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cells_mentor ON cells(mentor_id)")
        if trg_insert_sql:
            await conn.execute("DROP TRIGGER IF EXISTS trg_cell_capacity_insert")
            await conn.execute(trg_insert_sql)
        if trg_update_sql:
            await conn.execute("DROP TRIGGER IF EXISTS trg_cell_capacity_update")
            await conn.execute(trg_update_sql)
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.commit()

    # New v2 tables
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS weekly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(telegram_id),
            week_number INTEGER NOT NULL,
            plan_text TEXT,
            days_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS zoom_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            logged_by INTEGER NOT NULL REFERENCES users(telegram_id),
            week_number INTEGER NOT NULL,
            date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mock_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(telegram_id),
            exam_date TIMESTAMP NOT NULL,
            description TEXT,
            status TEXT CHECK(status IN ('scheduled', 'finished', 'cancelled')) DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mock_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mock_id INTEGER NOT NULL REFERENCES mock_exams(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            score_raw REAL,
            points_awarded INTEGER DEFAULT 0,
            entered_by INTEGER NOT NULL REFERENCES users(telegram_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mock_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS tasks_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            cycle_date DATE NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cell_id, user_id, cycle_date)
        );

        CREATE TABLE IF NOT EXISTS scores_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            cell_id INTEGER REFERENCES cells(id) ON DELETE SET NULL,
            points INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_weekly_plans_cell ON weekly_plans(cell_id, week_number);
        CREATE INDEX IF NOT EXISTS idx_zoom_logs_cell ON zoom_logs(cell_id, week_number);
        CREATE INDEX IF NOT EXISTS idx_mock_exams_cell ON mock_exams(cell_id, exam_date);
        CREATE INDEX IF NOT EXISTS idx_mock_scores_mock ON mock_scores(mock_id);
        CREATE INDEX IF NOT EXISTS idx_mock_scores_user ON mock_scores(user_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_progress_cell_date ON tasks_progress(cell_id, cycle_date);
        CREATE INDEX IF NOT EXISTS idx_tasks_progress_user ON tasks_progress(user_id);
        CREATE INDEX IF NOT EXISTS idx_scores_ledger_user ON scores_ledger(user_id);
        CREATE INDEX IF NOT EXISTS idx_scores_ledger_cell ON scores_ledger(cell_id);
        """
    )
    await conn.commit()

    # mock_exams: is_archived flag for the mock-date scheduling feature
    # (mentor can archive a past/cancelled mock date without deleting its
    # history, distinct from 'status' which tracks finished/cancelled).
    cur = await conn.execute("PRAGMA table_info(mock_exams)")
    mock_exam_columns = [row[1] for row in await cur.fetchall()]
    if "is_archived" not in mock_exam_columns:
        await conn.execute("ALTER TABLE mock_exams ADD COLUMN is_archived BOOLEAN DEFAULT 0")
        await conn.commit()

    # Per-user cross-cell quota triggers
    cur = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name IN "
        "('trg_partner_quota_insert', 'trg_partner_quota_update', 'trg_mentor_quota_insert')"
    )
    existing_names = {row[0] for row in await cur.fetchall()}

    if "trg_partner_quota_insert" not in existing_names:
        await conn.execute(
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
    if "trg_partner_quota_update" not in existing_names:
        await conn.execute(
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
    if "trg_mentor_quota_insert" not in existing_names:
        await conn.execute(
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
    await conn.commit()

    await _ensure_weekly_plan_v2_schema()
    await _ensure_zoom_v2_schema()


async def _ensure_weekly_plan_v2_schema() -> None:
    """Extends weekly_plans with structured per-day storage + per-day partner
    checkins, on top of the plain-text weekly_plans row created by
    _ensure_v2_schema(). Idempotent (safe on every startup)."""
    conn = get_conn()

    cur = await conn.execute("PRAGMA table_info(weekly_plans)")
    wp_columns = [row[1] for row in await cur.fetchall()]
    if "source_file_name" not in wp_columns:
        await conn.execute("ALTER TABLE weekly_plans ADD COLUMN source_file_name TEXT")
    if "parse_method" not in wp_columns:
        await conn.execute("ALTER TABLE weekly_plans ADD COLUMN parse_method TEXT")
    if "is_active" not in wp_columns:
        await conn.execute("ALTER TABLE weekly_plans ADD COLUMN is_active BOOLEAN DEFAULT 1")
    await conn.commit()

    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS weekly_plan_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
            day_number INTEGER NOT NULL CHECK(day_number BETWEEN 1 AND 7),
            day_date DATE,
            content TEXT NOT NULL,
            distributed BOOLEAN DEFAULT 0,
            UNIQUE(plan_id, day_number)
        );

        CREATE TABLE IF NOT EXISTS weekly_plan_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_day_id INTEGER NOT NULL REFERENCES weekly_plan_days(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            status TEXT CHECK(status IN ('kutilmoqda', 'bajardim', 'bajarmadim')) DEFAULT 'kutilmoqda',
            responded_at TIMESTAMP,
            reminder_sent BOOLEAN DEFAULT 0,
            mentor_confirmed BOOLEAN DEFAULT 0,
            points_awarded INTEGER DEFAULT 0,
            UNIQUE(plan_day_id, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_weekly_plan_days_plan ON weekly_plan_days(plan_id);
        CREATE INDEX IF NOT EXISTS idx_weekly_plan_checkins_day ON weekly_plan_checkins(plan_day_id);
        CREATE INDEX IF NOT EXISTS idx_weekly_plan_checkins_user ON weekly_plan_checkins(user_id);
        """
    )
    await conn.commit()

    cur = await conn.execute("PRAGMA table_info(weekly_plan_days)")
    wpd_columns = [row[1] for row in await cur.fetchall()]
    if "distributed" not in wpd_columns:
        await conn.execute("ALTER TABLE weekly_plan_days ADD COLUMN distributed BOOLEAN DEFAULT 0")
        await conn.commit()


async def _ensure_zoom_v2_schema() -> None:
    """Full Zoom scheduling system: sessions, partner time suggestions, and
    post-session confirmations. Separate from the pre-existing zoom_logs
    table (simple 'lesson happened this week' tally), which is left as-is."""
    conn = get_conn()

    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS zoom_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(telegram_id),
            session_at TIMESTAMP NOT NULL,
            note TEXT,
            status TEXT CHECK(status IN ('scheduled', 'done', 'cancelled')) DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS zoom_time_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            kind TEXT CHECK(kind IN ('conflict', 'preference')) NOT NULL,
            message TEXT NOT NULL,
            zoom_session_id INTEGER REFERENCES zoom_sessions(id) ON DELETE SET NULL,
            is_resolved BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS zoom_confirmations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zoom_session_id INTEGER NOT NULL REFERENCES zoom_sessions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(telegram_id),
            attended TEXT CHECK(attended IN ('yes', 'no', 'no_response')) DEFAULT 'no_response',
            reason TEXT,
            responded_at TIMESTAMP,
            UNIQUE(zoom_session_id, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_zoom_sessions_cell ON zoom_sessions(cell_id, session_at);
        CREATE INDEX IF NOT EXISTS idx_zoom_suggestions_cell ON zoom_time_suggestions(cell_id, is_resolved);
        CREATE INDEX IF NOT EXISTS idx_zoom_confirmations_session ON zoom_confirmations(zoom_session_id);
        """
    )
    await conn.commit()


async def close_db() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None


def get_conn() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return _connection


@asynccontextmanager
async def tx() -> AsyncIterator[aiosqlite.Connection]:
    """Explicit transaction context manager: commits on success, rolls back on error."""
    conn = get_conn()
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
