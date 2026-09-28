from __future__ import annotations

from typing import Optional

import aiosqlite

from database.db import get_conn
from database.repo_cells import list_cell_partners


async def create_task(cell_id: int, created_by: int, title: str, description: str, deadline_str: str) -> int:
    """deadline_str must be 'YYYY-MM-DD HH:MM:SS' in Asia/Tashkent naive local time."""
    conn = get_conn()
    cur = await conn.execute(
        """
        INSERT INTO tasks (cell_id, created_by, title, description, deadline)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cell_id, created_by, title, description, deadline_str),
    )
    task_id = cur.lastrowid
    partners = await list_cell_partners(cell_id)
    for p in partners:
        await conn.execute(
            "INSERT INTO submissions (task_id, user_id, status) VALUES (?, ?, 'kutilmoqda')",
            (task_id, p["telegram_id"]),
        )
    await conn.commit()
    return task_id


async def get_task(task_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return await cur.fetchone()


async def update_task_deadline(task_id: int, new_deadline_str: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE tasks SET deadline = ? WHERE id = ?", (new_deadline_str, task_id))
    await conn.commit()


async def close_task(task_id: int, status: str = "closed") -> None:
    conn = get_conn()
    await conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    await conn.commit()


async def list_active_tasks_for_cell(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM tasks WHERE cell_id = ? AND status = 'active' ORDER BY deadline",
        (cell_id,),
    )
    return list(await cur.fetchall())


async def list_active_tasks_for_partner(partner_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT t.*, s.status AS my_status, s.id AS submission_id, c.direction_id, d.name AS direction_name
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        JOIN cells c ON c.id = t.cell_id
        JOIN directions d ON d.id = c.direction_id
        WHERE s.user_id = ? AND t.status = 'active' AND s.status != 'bajardi'
        ORDER BY t.deadline
        """,
        (partner_id,),
    )
    return list(await cur.fetchall())


async def list_all_tasks_for_partner(partner_id: int) -> list[aiosqlite.Row]:
    """Same as list_active_tasks_for_partner but includes completed ('bajardi')
    tasks too. Used for statistics where completed tasks must still count."""
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT t.*, s.status AS my_status, s.id AS submission_id, c.direction_id, d.name AS direction_name
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        JOIN cells c ON c.id = t.cell_id
        JOIN directions d ON d.id = c.direction_id
        WHERE s.user_id = ? AND t.status = 'active'
        ORDER BY t.deadline
        """,
        (partner_id,),
    )
    return list(await cur.fetchall())


async def get_submission(submission_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    return await cur.fetchone()


async def update_submission_status(submission_id: int, status: str, notes: Optional[str] = None) -> None:
    conn = get_conn()
    if status == "bajardi":
        await conn.execute(
            "UPDATE submissions SET status = ?, submitted_at = CURRENT_TIMESTAMP, notes = COALESCE(?, notes) WHERE id = ?",
            (status, notes, submission_id),
        )
    else:
        await conn.execute(
            "UPDATE submissions SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
            (status, notes, submission_id),
        )
    await conn.commit()


async def list_submissions_for_task(task_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT s.*, u.full_name, u.username
        FROM submissions s
        JOIN users u ON u.telegram_id = s.user_id
        WHERE s.task_id = ?
        """,
        (task_id,),
    )
    return list(await cur.fetchall())


async def count_completed_submissions(user_id: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM submissions WHERE user_id = ? AND status = 'bajardi'",
        (user_id,),
    )
    row = await cur.fetchone()
    return int(row["cnt"])


async def list_pending_submissions_for_task(task_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT s.*, u.full_name, u.username
        FROM submissions s
        JOIN users u ON u.telegram_id = s.user_id
        WHERE s.task_id = ? AND s.status IN ('kutilmoqda', 'jarayonda')
        """,
        (task_id,),
    )
    return list(await cur.fetchall())


async def list_tasks_with_upcoming_deadline_in_window(start_str: str, end_str: str) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT * FROM tasks
        WHERE status = 'active' AND deadline BETWEEN ? AND ?
        """,
        (start_str, end_str),
    )
    return list(await cur.fetchall())


async def list_overdue_tasks(now_str: str) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM tasks WHERE status = 'active' AND deadline < ?",
        (now_str,),
    )
    return list(await cur.fetchall())


async def list_all_active_tasks() -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM tasks WHERE status = 'active'")
    return list(await cur.fetchall())
