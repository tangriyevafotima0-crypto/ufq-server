"""
database/repo_zoom.py
-----------------------
Repo functions for the full Zoom scheduling system (zoom_sessions,
zoom_time_suggestions, zoom_confirmations) -- distinct from the pre-existing
zoom_logs 'lesson happened this week' tally in database/repo_v2.py.
"""

from __future__ import annotations

from typing import Optional

import aiosqlite

from database.db import get_conn


# ---------- zoom_sessions ----------

async def create_zoom_session(cell_id: int, created_by: int, session_at_str: str,
                               note: Optional[str] = None) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "INSERT INTO zoom_sessions (cell_id, created_by, session_at, note) VALUES (?, ?, ?, ?)",
        (cell_id, created_by, session_at_str, note),
    )
    await conn.commit()
    return cur.lastrowid


async def get_zoom_session(session_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM zoom_sessions WHERE id = ?", (session_id,))
    return await cur.fetchone()


async def update_zoom_session_time(session_id: int, session_at_str: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE zoom_sessions SET session_at = ? WHERE id = ?", (session_at_str, session_id))
    await conn.commit()


async def delete_zoom_session(session_id: int) -> None:
    conn = get_conn()
    await conn.execute("DELETE FROM zoom_sessions WHERE id = ?", (session_id,))
    await conn.commit()


async def set_zoom_session_status(session_id: int, status: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE zoom_sessions SET status = ? WHERE id = ?", (status, session_id))
    await conn.commit()


async def list_upcoming_zoom_sessions_for_cell(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM zoom_sessions WHERE cell_id = ? AND status = 'scheduled' "
        "AND session_at >= datetime('now', '-1 hour') ORDER BY session_at",
        (cell_id,),
    )
    return await cur.fetchall()


async def list_all_zoom_sessions_for_cell(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM zoom_sessions WHERE cell_id = ? ORDER BY session_at DESC", (cell_id,)
    )
    return await cur.fetchall()


async def list_due_scheduled_sessions() -> list[aiosqlite.Row]:
    """Sessions whose time has passed but are still 'scheduled' (for the
    scheduler to fire the +1h post-check and then archive)."""
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM zoom_sessions WHERE status = 'scheduled' AND session_at <= datetime('now')"
    )
    return await cur.fetchall()


# ---------- zoom_time_suggestions ----------

async def add_time_suggestion(cell_id: int, user_id: int, kind: str, message: str) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "INSERT INTO zoom_time_suggestions (cell_id, user_id, kind, message) VALUES (?, ?, ?, ?)",
        (cell_id, user_id, kind, message),
    )
    await conn.commit()
    return cur.lastrowid


async def list_unresolved_suggestions_for_cell(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT s.*, u.full_name FROM zoom_time_suggestions s
        JOIN users u ON u.telegram_id = s.user_id
        WHERE s.cell_id = ? AND s.is_resolved = 0
        ORDER BY s.created_at
        """,
        (cell_id,),
    )
    return await cur.fetchall()


async def resolve_suggestions_for_cell(cell_id: int, zoom_session_id: int) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE zoom_time_suggestions SET is_resolved = 1, zoom_session_id = ? "
        "WHERE cell_id = ? AND is_resolved = 0",
        (zoom_session_id, cell_id),
    )
    await conn.commit()


# ---------- zoom_confirmations ----------

async def ensure_confirmation_rows(zoom_session_id: int, user_ids: list[int]) -> None:
    conn = get_conn()
    for uid in user_ids:
        await conn.execute(
            "INSERT OR IGNORE INTO zoom_confirmations (zoom_session_id, user_id) VALUES (?, ?)",
            (zoom_session_id, uid),
        )
    await conn.commit()


async def set_confirmation(zoom_session_id: int, user_id: int, attended: str, reason: Optional[str] = None) -> None:
    conn = get_conn()
    await conn.execute(
        """
        UPDATE zoom_confirmations
        SET attended = ?, reason = ?, responded_at = CURRENT_TIMESTAMP
        WHERE zoom_session_id = ? AND user_id = ?
        """,
        (attended, reason, zoom_session_id, user_id),
    )
    await conn.commit()


async def list_confirmations_for_session(zoom_session_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, u.full_name FROM zoom_confirmations c
        JOIN users u ON u.telegram_id = c.user_id
        WHERE c.zoom_session_id = ?
        """,
        (zoom_session_id,),
    )
    return await cur.fetchall()


async def list_no_responses_for_session(zoom_session_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM zoom_confirmations WHERE zoom_session_id = ? AND attended = 'no'",
        (zoom_session_id,),
    )
    return await cur.fetchall()
