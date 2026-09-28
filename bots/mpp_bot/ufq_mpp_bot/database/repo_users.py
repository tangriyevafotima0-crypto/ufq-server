from __future__ import annotations

from typing import Optional

import aiosqlite

from database.db import get_conn, tx


async def upsert_user(telegram_id: int, full_name: str, username: Optional[str]) -> None:
    conn = get_conn()
    await conn.execute(
        """
        INSERT INTO users (telegram_id, full_name, username)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            full_name = excluded.full_name,
            username = excluded.username
        """,
        (telegram_id, full_name, username),
    )
    await conn.commit()


async def get_user(telegram_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    return await cur.fetchone()


async def get_user_by_username(username: str) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    uname = username.lstrip("@")
    cur = await conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (uname,))
    return await cur.fetchone()


async def is_admin(telegram_id: int) -> bool:
    row = await get_user(telegram_id)
    return bool(row["is_admin"]) if row else False


async def set_admin(telegram_id: int, value: bool = True) -> None:
    conn = get_conn()
    await conn.execute("UPDATE users SET is_admin = ? WHERE telegram_id = ?", (int(value), telegram_id))
    await conn.commit()


async def list_all_users() -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM users ORDER BY full_name COLLATE NOCASE")
    return list(await cur.fetchall())


async def get_user_roles_in_cells(telegram_id: int) -> list[dict]:
    """Every direction this user is involved in, tagged with role
    (mentor/partner), for the admin profile card."""
    conn = get_conn()
    roles: list[dict] = []
    cur = await conn.execute(
        """
        SELECT d.name AS direction_name, c.id AS cell_id
        FROM cells c JOIN directions d ON d.id = c.direction_id
        WHERE c.mentor_id = ? AND c.is_active = 1
        """,
        (telegram_id,),
    )
    for row in await cur.fetchall():
        roles.append({"direction_name": row["direction_name"], "cell_id": row["cell_id"], "role": "mentor"})
    cur = await conn.execute(
        """
        SELECT d.name AS direction_name, c.id AS cell_id
        FROM cell_members cm
        JOIN cells c ON c.id = cm.cell_id
        JOIN directions d ON d.id = c.direction_id
        WHERE cm.partner_id = ? AND cm.is_active = 1 AND c.is_active = 1
        """,
        (telegram_id,),
    )
    for row in await cur.fetchall():
        roles.append({"direction_name": row["direction_name"], "cell_id": row["cell_id"], "role": "partner"})
    return roles


async def search_users(query: str, limit: int = 10) -> list[aiosqlite.Row]:
    conn = get_conn()
    like = f"%{query}%"
    cur = await conn.execute(
        """
        SELECT * FROM users
        WHERE full_name LIKE ? OR username LIKE ?
        ORDER BY full_name COLLATE NOCASE
        LIMIT ?
        """,
        (like, like, limit),
    )
    return list(await cur.fetchall())
