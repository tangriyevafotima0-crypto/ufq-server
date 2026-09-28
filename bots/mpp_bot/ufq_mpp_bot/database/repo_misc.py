from __future__ import annotations

import aiosqlite

from database.db import get_conn


# ---------- reminders_log ----------

async def has_reminder_been_sent(task_id: int, user_id: int, reminder_type: str) -> bool:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT 1 FROM reminders_log WHERE task_id = ? AND user_id = ? AND reminder_type = ?",
        (task_id, user_id, reminder_type),
    )
    return (await cur.fetchone()) is not None


async def log_reminder(task_id: int, user_id: int, reminder_type: str) -> None:
    conn = get_conn()
    await conn.execute(
        "INSERT INTO reminders_log (task_id, user_id, reminder_type) VALUES (?, ?, ?)",
        (task_id, user_id, reminder_type),
    )
    await conn.commit()


# ---------- mock_results ----------

async def add_mock_result(user_id: int, direction_id: int, entered_by: int, score: float, date_str: str) -> int:
    conn = get_conn()
    cur = await conn.execute(
        """
        INSERT INTO mock_results (user_id, direction_id, entered_by, score, date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, direction_id, entered_by, score, date_str),
    )
    await conn.commit()
    return cur.lastrowid


async def list_mock_results_for_user(user_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT m.*, d.name AS direction_name
        FROM mock_results m
        JOIN directions d ON d.id = m.direction_id
        WHERE m.user_id = ?
        ORDER BY m.date
        """,
        (user_id,),
    )
    return list(await cur.fetchall())


async def list_mock_results_for_direction(direction_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT m.*, u.full_name
        FROM mock_results m
        JOIN users u ON u.telegram_id = m.user_id
        WHERE m.direction_id = ?
        ORDER BY m.date
        """,
        (direction_id,),
    )
    return list(await cur.fetchall())


async def list_all_mock_results() -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT m.*, u.full_name, d.name AS direction_name
        FROM mock_results m
        JOIN users u ON u.telegram_id = m.user_id
        JOIN directions d ON d.id = m.direction_id
        ORDER BY m.date
        """
    )
    return list(await cur.fetchall())
