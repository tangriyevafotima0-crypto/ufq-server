"""
database/repo_weekly_plan.py
------------------------------
Repo functions for the structured per-day weekly plan tables
(weekly_plan_days, weekly_plan_checkins) added on top of the plain-text
weekly_plans row from database/repo_v2.py.
"""

from __future__ import annotations

from typing import Optional

import aiosqlite

from database.db import get_conn


async def set_source_meta(plan_id: int, source_file_name: Optional[str], parse_method: str) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE weekly_plans SET source_file_name = ?, parse_method = ? WHERE id = ?",
        (source_file_name, parse_method, plan_id),
    )
    await conn.commit()


async def deactivate_previous_plans(cell_id: int) -> None:
    """Marks all older plans for this cell inactive so only the latest one
    drives daily distribution/checkins (mentor can still see history)."""
    conn = get_conn()
    await conn.execute("UPDATE weekly_plans SET is_active = 0 WHERE cell_id = ?", (cell_id,))
    await conn.commit()


async def insert_plan_day(
    plan_id: int, day_number: int, day_date: Optional[str], content: str, distributed: bool = False
) -> int:
    conn = get_conn()
    cur = await conn.execute(
        """
        INSERT INTO weekly_plan_days (plan_id, day_number, day_date, content, distributed)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(plan_id, day_number) DO UPDATE SET content = excluded.content, day_date = excluded.day_date
        """,
        (plan_id, day_number, day_date, content, 1 if distributed else 0),
    )
    await conn.commit()
    return cur.lastrowid


async def mark_plan_day_distributed(plan_day_id: int) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE weekly_plan_days SET distributed = 1 WHERE id = ?", (plan_day_id,)
    )
    await conn.commit()


async def list_plan_days_pending_distribution() -> list[aiosqlite.Row]:
    """Days whose scheduled date has arrived but haven't been pushed to
    partners yet -- used by the daily auto-distribution scheduler job."""
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT d.*, p.cell_id
        FROM weekly_plan_days d
        JOIN weekly_plans p ON p.id = d.plan_id
        WHERE d.distributed = 0
          AND p.is_active = 1
          AND d.day_date IS NOT NULL
          AND date(d.day_date) <= date('now')
        """
    )
    return await cur.fetchall()


async def list_plan_days(plan_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM weekly_plan_days WHERE plan_id = ? ORDER BY day_number", (plan_id,)
    )
    return await cur.fetchall()


async def get_plan_day(plan_id: int, day_number: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM weekly_plan_days WHERE plan_id = ? AND day_number = ?", (plan_id, day_number)
    )
    return await cur.fetchone()


async def get_active_plan_for_cell(cell_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM weekly_plans WHERE cell_id = ? AND is_active = 1 "
        "ORDER BY week_number DESC, created_at DESC LIMIT 1",
        (cell_id,),
    )
    return await cur.fetchone()


async def delete_plan(plan_id: int) -> None:
    conn = get_conn()
    await conn.execute("DELETE FROM weekly_plans WHERE id = ?", (plan_id,))
    await conn.commit()


# ---------- checkins ----------

async def ensure_checkin_rows(plan_day_id: int, user_ids: list[int]) -> None:
    conn = get_conn()
    for uid in user_ids:
        await conn.execute(
            "INSERT OR IGNORE INTO weekly_plan_checkins (plan_day_id, user_id) VALUES (?, ?)",
            (plan_day_id, uid),
        )
    await conn.commit()


async def get_checkin(plan_day_id: int, user_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM weekly_plan_checkins WHERE plan_day_id = ? AND user_id = ?",
        (plan_day_id, user_id),
    )
    return await cur.fetchone()


async def set_checkin_status(plan_day_id: int, user_id: int, status: str) -> None:
    conn = get_conn()
    await conn.execute(
        """
        UPDATE weekly_plan_checkins
        SET status = ?, responded_at = CURRENT_TIMESTAMP
        WHERE plan_day_id = ? AND user_id = ?
        """,
        (status, plan_day_id, user_id),
    )
    await conn.commit()


async def mark_reminder_sent(plan_day_id: int, user_id: int) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE weekly_plan_checkins SET reminder_sent = 1 WHERE plan_day_id = ? AND user_id = ?",
        (plan_day_id, user_id),
    )
    await conn.commit()


async def list_pending_checkins_needing_reminder() -> list[aiosqlite.Row]:
    """Rows still 'kutilmoqda' for a day whose date has passed, and no
    reminder sent yet -- used by the every-2-3-day auto-prompt job."""
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, d.plan_id, d.day_number, d.content, d.day_date, p.cell_id
        FROM weekly_plan_checkins c
        JOIN weekly_plan_days d ON d.id = c.plan_day_id
        JOIN weekly_plans p ON p.id = d.plan_id
        WHERE c.status = 'kutilmoqda' AND c.reminder_sent = 0
          AND p.is_active = 1
          AND (d.day_date IS NULL OR date(d.day_date) <= date('now'))
        """
    )
    return await cur.fetchall()


async def confirm_checkin_and_award(plan_day_id: int, user_id: int, points: int) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE weekly_plan_checkins SET mentor_confirmed = 1, points_awarded = ? "
        "WHERE plan_day_id = ? AND user_id = ?",
        (points, plan_day_id, user_id),
    )
    await conn.commit()


async def list_checkins_for_plan_day(plan_day_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM weekly_plan_checkins WHERE plan_day_id = ?", (plan_day_id,)
    )
    return await cur.fetchall()


async def list_unconfirmed_done_checkins_for_cell(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, d.day_number, d.content, u.full_name
        FROM weekly_plan_checkins c
        JOIN weekly_plan_days d ON d.id = c.plan_day_id
        JOIN weekly_plans p ON p.id = d.plan_id
        JOIN users u ON u.telegram_id = c.user_id
        WHERE p.cell_id = ? AND p.is_active = 1
          AND c.status = 'bajardim' AND c.mentor_confirmed = 0
        ORDER BY d.day_number
        """,
        (cell_id,),
    )
    return await cur.fetchall()
