from __future__ import annotations

from typing import Optional

import aiosqlite

from database.db import get_conn


async def create_direction(name: str) -> int:
    conn = get_conn()
    cur = await conn.execute("SELECT id FROM directions WHERE name = ?", (name,))
    row = await cur.fetchone()
    if row:
        return row[0]
    cur = await conn.execute("INSERT INTO directions (name) VALUES (?)", (name,))
    await conn.commit()
    return cur.lastrowid


async def get_direction(direction_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM directions WHERE id = ?", (direction_id,))
    return await cur.fetchone()


async def list_directions(active_only: bool = False) -> list[aiosqlite.Row]:
    conn = get_conn()
    if active_only:
        cur = await conn.execute("SELECT * FROM directions WHERE is_active = 1 ORDER BY name")
    else:
        cur = await conn.execute("SELECT * FROM directions ORDER BY name")
    return list(await cur.fetchall())


async def toggle_direction(direction_id: int) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE directions SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (direction_id,),
    )
    await conn.commit()


async def direction_name_exists(name: str) -> bool:
    conn = get_conn()
    cur = await conn.execute("SELECT 1 FROM directions WHERE name = ? COLLATE NOCASE", (name,))
    return (await cur.fetchone()) is not None


async def set_direction_category(direction_id: int, category: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE directions SET category = ? WHERE id = ?", (category, direction_id))
    await conn.commit()


async def rename_direction(direction_id: int, new_name: str) -> None:
    conn = get_conn()
    await conn.execute("UPDATE directions SET name = ? WHERE id = ?", (new_name, direction_id))
    await conn.commit()


async def archive_direction(direction_id: int) -> None:
    """Soft-delete: keeps history/points intact, just deactivates the
    direction and cascades is_active=0 to its cells so it disappears from
    active listings without losing any data."""
    conn = get_conn()
    await conn.execute("UPDATE directions SET is_active = 0 WHERE id = ?", (direction_id,))
    await conn.execute("UPDATE cells SET is_active = 0 WHERE direction_id = ?", (direction_id,))
    await conn.commit()


async def count_cells_in_direction(direction_id: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM cells WHERE direction_id = ? AND is_active = 1",
        (direction_id,),
    )
    row = await cur.fetchone()
    return int(row["cnt"])
