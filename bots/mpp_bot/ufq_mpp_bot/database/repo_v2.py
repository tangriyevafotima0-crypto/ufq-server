"""
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
        "SELECT * FROM mock_exams WHERE cell_id = ? AND status = 'scheduled' AND is_archived = 0 ORDER BY exam_date",
        (cell_id,),
    )
    return list(await cur.fetchall())


async def list_all_mock_exams_for_cell(cell_id: int, include_archived: bool = True) -> list[aiosqlite.Row]:
    """All mock dates for a cell (scheduled/finished/cancelled), for display
    in the group profile screen visible to admin/mentor/partner."""
    conn = get_conn()
    if include_archived:
        cur = await conn.execute(
            "SELECT * FROM mock_exams WHERE cell_id = ? ORDER BY exam_date",
            (cell_id,),
        )
    else:
        cur = await conn.execute(
            "SELECT * FROM mock_exams WHERE cell_id = ? AND is_archived = 0 ORDER BY exam_date",
            (cell_id,),
        )
    return list(await cur.fetchall())


async def mark_mock_exam_finished(mock_id: int) -> None:
    conn = get_conn()
    await conn.execute("UPDATE mock_exams SET status = 'finished' WHERE id = ?", (mock_id,))
    await conn.commit()


async def archive_mock_exam(mock_id: int) -> None:
    conn = get_conn()
    await conn.execute("UPDATE mock_exams SET is_archived = 1 WHERE id = ?", (mock_id,))
    await conn.commit()


async def unarchive_mock_exam(mock_id: int) -> None:
    conn = get_conn()
    await conn.execute("UPDATE mock_exams SET is_archived = 0 WHERE id = ?", (mock_id,))
    await conn.commit()


async def update_mock_exam_description(mock_id: int, description: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE mock_exams SET description = ? WHERE id = ?", (description, mock_id))
    await conn.commit()


async def count_mock_exams_in_month_for_cell(cell_id: int, year: int, month: int) -> int:
    """Count non-archived mocks already scheduled for this cell within the
    given calendar month, used to auto-name a new mock as 'N-chi mock'."""
    conn = get_conn()
    month_prefix = f"{year:04d}-{month:02d}"
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM mock_exams WHERE cell_id = ? AND is_archived = 0 AND exam_date LIKE ?",
        (cell_id, f"{month_prefix}%"),
    )
    row = await cur.fetchone()
    return int(row["cnt"])


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


async def get_task_progress(cell_id: int, user_id: int, cycle_date_str: str) -> Optional[aiosqlite.Row]:
    """Look up an existing check-in row for this cell/user/cycle, so the UI
    can avoid re-asking (and re-awarding points) once a partner has already
    marked a cycle as done/failed."""
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM tasks_progress WHERE cell_id = ? AND user_id = ? AND cycle_date = ?",
        (cell_id, user_id, cycle_date_str),
    )
    return await cur.fetchone()


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


# ---------- directory (peer_to_peer-safe cell listing) ----------

async def list_all_cells_including_peer_to_peer() -> list[aiosqlite.Row]:
    """Like database.repo_cells.list_all_cells(), but uses a LEFT JOIN on
    users so cells with mentor_id IS NULL (peer_to_peer cells, possible
    since patch_and_update.py made cells.mentor_id nullable) are still
    included instead of being silently dropped by an INNER JOIN.

    mentor_name / mentor_username are NULL for peer_to_peer cells -- callers
    should treat NULL there as "no mentor" rather than "mentor lookup failed".
    """
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, d.name AS direction_name, u.full_name AS mentor_name, u.username AS mentor_username
        FROM cells c
        JOIN directions d ON d.id = c.direction_id
        LEFT JOIN users u ON u.telegram_id = c.mentor_id
        WHERE c.is_active = 1
        ORDER BY d.name, COALESCE(u.full_name, '')
        """
    )
    return list(await cur.fetchall())
