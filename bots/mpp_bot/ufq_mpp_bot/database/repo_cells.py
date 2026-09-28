from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite

from database.db import get_conn
from utils.timez import now_tz

MAX_PARTNERS = 3


class CellError(Exception):
    """Domain-level error for cell operations (surfaced as user-facing messages)."""


async def create_cell(direction_id: int, mentor_id: Optional[int] = None) -> int:
    conn = get_conn()
    if mentor_id is not None:
        # A mentor may hold only one active cell per direction.
        cur = await conn.execute(
            "SELECT 1 FROM cells WHERE direction_id = ? AND mentor_id = ? AND is_active = 1",
            (direction_id, mentor_id),
        )
        if await cur.fetchone():
            raise CellError("Bu foydalanuvchi ushbu yo'nalishda allaqachon mentor.")
    cur = await conn.execute(
        "INSERT INTO cells (direction_id, mentor_id) VALUES (?, ?)",
        (direction_id, mentor_id),
    )
    await conn.commit()
    return cur.lastrowid


async def get_cell(cell_id: int) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM cells WHERE id = ?", (cell_id,))
    return await cur.fetchone()


async def list_cells_for_mentor(mentor_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, d.name AS direction_name
        FROM cells c
        JOIN directions d ON d.id = c.direction_id
        WHERE c.mentor_id = ? AND c.is_active = 1
        ORDER BY d.name
        """,
        (mentor_id,),
    )
    return list(await cur.fetchall())


async def list_all_cells() -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, d.name AS direction_name, u.full_name AS mentor_name, u.username AS mentor_username
        FROM cells c
        JOIN directions d ON d.id = c.direction_id
        JOIN users u ON u.telegram_id = c.mentor_id
        WHERE c.is_active = 1
        ORDER BY d.name, u.full_name
        """
    )
    return list(await cur.fetchall())


async def active_partner_count(cell_id: int) -> int:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM cell_members WHERE cell_id = ? AND is_active = 1",
        (cell_id,),
    )
    row = await cur.fetchone()
    return int(row["cnt"])


async def list_cell_partners(cell_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT u.*, cm.joined_at
        FROM cell_members cm
        JOIN users u ON u.telegram_id = cm.partner_id
        WHERE cm.cell_id = ? AND cm.is_active = 1
        ORDER BY cm.joined_at
        """,
        (cell_id,),
    )
    return list(await cur.fetchall())


async def is_partner_in_cell(cell_id: int, partner_id: int) -> bool:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT 1 FROM cell_members WHERE cell_id = ? AND partner_id = ? AND is_active = 1",
        (cell_id, partner_id),
    )
    return (await cur.fetchone()) is not None


async def assert_mentor_owns_cell(mentor_id: int, cell_id: int):
    """Raise CellError if `mentor_id` is not the mentor of `cell_id`.

    Used to close an IDOR gap: a mentor could otherwise craft/replay a
    callback_data string with another mentor's cell_id and manage a cell
    that isn't theirs (add/remove partners, assign tasks, etc.).
    Returns the cell row on success, for callers that need it.
    """
    cell = await get_cell(cell_id)
    if cell is None or not cell["is_active"] or cell["mentor_id"] != mentor_id:
        raise CellError("Bu hujayrani boshqarish huquqiga ega emassiz.")
    return cell


async def add_partner(cell_id: int, partner_id: int) -> None:
    """Add a partner to a cell, enforcing capacity and self-mentorship guards.

    Also generates 'kutilmoqda' submission rows for every currently-active task
    in the cell, so a partner who joins after tasks were already assigned can
    still see and act on them (fixes the "blind late partner" gap).
    """
    conn = get_conn()
    cell = await get_cell(cell_id)
    if cell is None or not cell["is_active"]:
        raise CellError("Hujayra topilmadi yoki faol emas.")
    if partner_id == cell["mentor_id"]:
        raise CellError("Mentor o'zini o'z hujayrasiga partner sifatida qo'sha olmaydi.")
    if await is_partner_in_cell(cell_id, partner_id):
        raise CellError("Bu foydalanuvchi allaqachon ushbu hujayrada partner.")
    count = await active_partner_count(cell_id)
    if count >= MAX_PARTNERS:
        raise CellError(f"Hujayrada eng ko'pi bilan {MAX_PARTNERS} ta partner bo'lishi mumkin. Joy yo'q.")

    try:
        await conn.execute(
            """
            INSERT INTO cell_members (cell_id, partner_id, is_active)
            VALUES (?, ?, 1)
            ON CONFLICT(cell_id, partner_id) DO UPDATE SET is_active = 1, joined_at = CURRENT_TIMESTAMP
            """,
            (cell_id, partner_id),
        )
        # Backfill submissions for tasks that already existed in this cell,
        # so a newly added partner isn't "blind" to active work — but only
        # for tasks whose deadline hasn't passed yet. A task can be DB-status
        # 'active' while already overdue (pending the scheduler's overdue
        # sweep), and a late-joining partner shouldn't instantly inherit an
        # already-missed deadline. Deadlines are stored as naive Asia/Tashkent
        # local strings, so the "now" cutoff must be computed the same way
        # (not SQLite's datetime('now'), which is UTC).
        now_local_str = now_tz().strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute(
            """
            INSERT INTO submissions (task_id, user_id, status)
            SELECT t.id, ?, 'kutilmoqda'
            FROM tasks t
            WHERE t.cell_id = ? AND t.status = 'active' AND t.deadline > ?
              AND NOT EXISTS (
                  SELECT 1 FROM submissions s WHERE s.task_id = t.id AND s.user_id = ?
              )
            """,
            (partner_id, cell_id, now_local_str, partner_id),
        )
    except aiosqlite.IntegrityError as e:
        await conn.rollback()
        msg = str(e)
        if "CELL_FULL" in msg:
            raise CellError(f"Hujayrada eng ko'pi bilan {MAX_PARTNERS} ta partner bo'lishi mumkin. Joy yo'q.") from e
        if "FOREIGN KEY" in msg.upper():
            raise CellError(
                "Bu foydalanuvchi hali botni ishga tushirmagan (/start bosmagan). "
                "Avval unga botga /start bosishini so'rang, keyin qayta urinib ko'ring."
            ) from e
        raise CellError("Partner qo'shishda kutilmagan xatolik yuz berdi. Qayta urinib ko'ring.") from e
    await conn.commit()


async def remove_partner(cell_id: int, partner_id: int) -> None:
    conn = get_conn()
    await conn.execute(
        "UPDATE cell_members SET is_active = 0 WHERE cell_id = ? AND partner_id = ?",
        (cell_id, partner_id),
    )
    await conn.commit()


async def generate_invite_code(cell_id: int, ttl_hours: int = 24) -> str:
    """Generate a single-use 6-digit invite code for the cell, valid for ttl_hours."""
    conn = get_conn()
    cell = await get_cell(cell_id)
    if cell is None or not cell["is_active"]:
        raise CellError("Hujayra topilmadi yoki faol emas.")
    count = await active_partner_count(cell_id)
    if count >= MAX_PARTNERS:
        raise CellError(f"Hujayrada eng ko'pi bilan {MAX_PARTNERS} ta partner bo'lishi mumkin. Joy yo'q.")

    for _ in range(10):
        code = "".join(random.choices(string.digits, k=6))
        cur = await conn.execute("SELECT 1 FROM cells WHERE invite_code = ?", (code,))
        if not await cur.fetchone():
            break
    else:
        raise CellError("Kod generatsiya qilishda xatolik. Qayta urinib ko'ring.")

    expires_at = now_tz() + timedelta(hours=ttl_hours)
    await conn.execute(
        "UPDATE cells SET invite_code = ?, invite_code_expires_at = ? WHERE id = ?",
        (code, expires_at.strftime("%Y-%m-%d %H:%M:%S"), cell_id),
    )
    await conn.commit()
    return code


async def find_cell_by_invite_code(code: str) -> Optional[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        "SELECT * FROM cells WHERE invite_code = ? AND is_active = 1",
        (code,),
    )
    cell = await cur.fetchone()
    if cell is None:
        return None
    expires_raw = cell["invite_code_expires_at"]
    if expires_raw is None:
        return None
    expires_at = datetime.strptime(expires_raw, "%Y-%m-%d %H:%M:%S")
    if now_tz().replace(tzinfo=None) > expires_at:
        return None
    return cell


async def consume_invite_code(cell_id: int) -> None:
    """Invalidate an invite code after successful use (single-use semantics)."""
    conn = get_conn()
    await conn.execute(
        "UPDATE cells SET invite_code = NULL, invite_code_expires_at = NULL WHERE id = ?",
        (cell_id,),
    )
    await conn.commit()


async def get_cell_for_join_link(cell_id: int) -> Optional[aiosqlite.Row]:
    """Resolve a cell for the persistent deep-link (?start=join_<id>), which
    unlike the 6-digit invite code never expires and is always the same URL
    for the cell's lifetime. Only returns active cells."""
    conn = get_conn()
    cur = await conn.execute("SELECT * FROM cells WHERE id = ? AND is_active = 1", (cell_id,))
    return await cur.fetchone()


async def get_cells_for_partner(partner_id: int) -> list[aiosqlite.Row]:
    conn = get_conn()
    cur = await conn.execute(
        """
        SELECT c.*, d.name AS direction_name, u.full_name AS mentor_name
        FROM cell_members cm
        JOIN cells c ON c.id = cm.cell_id
        JOIN directions d ON d.id = c.direction_id
        JOIN users u ON u.telegram_id = c.mentor_id
        WHERE cm.partner_id = ? AND cm.is_active = 1 AND c.is_active = 1
        """,
        (partner_id,),
    )
    return list(await cur.fetchall())


async def set_cell_mentor(cell_id: int, mentor_id: int) -> None:
    """Assign or change the mentor of an existing cell (used by the admin
    drill-down tree's 'Mentor tayinlash / o'zgartirish' action)."""
    conn = get_conn()
    cur = await conn.execute(
        "SELECT 1 FROM cells WHERE direction_id = (SELECT direction_id FROM cells WHERE id = ?) "
        "AND mentor_id = ? AND is_active = 1 AND id != ?",
        (cell_id, mentor_id, cell_id),
    )
    if await cur.fetchone():
        raise CellError("Bu foydalanuvchi ushbu yo'nalishda allaqachon boshqa guruhda mentor.")
    await conn.execute("UPDATE cells SET mentor_id = ? WHERE id = ?", (mentor_id, cell_id))
    await conn.commit()


async def release_cell_mentor(cell_id: int) -> None:
    conn = get_conn()
    await conn.execute("UPDATE cells SET mentor_id = NULL WHERE id = ?", (cell_id,))
    await conn.commit()


async def deactivate_cell(cell_id: int) -> None:
    conn = get_conn()
    await conn.execute("UPDATE cells SET is_active = 0 WHERE id = ?", (cell_id,))
    await conn.commit()


async def rename_cell(cell_id: int, new_label: str) -> None:
    """Cells are identified by direction + mentor by default; this adds an
    optional free-text label column (created on first use) so admins can
    give a cell its own display name (e.g. "SAT Team 1")."""
    conn = get_conn()
    await _ensure_label_column(conn)
    await conn.execute("UPDATE cells SET label = ? WHERE id = ?", (new_label, cell_id))
    await conn.commit()


async def move_partner_to_cell(from_cell_id: int, to_cell_id: int, partner_id: int) -> None:
    """Move a partner from one cell to another (remove_partner + add_partner
    combined into one operation, used by the admin profile-card 'move to
    another cell' action)."""
    await remove_partner(from_cell_id, partner_id)
    await add_partner(to_cell_id, partner_id)


async def get_cells_for_direction(direction_id: int, include_inactive: bool = False) -> list[aiosqlite.Row]:
    conn = get_conn()
    await _ensure_label_column(conn)
    if include_inactive:
        cur = await conn.execute(
            """
            SELECT c.*, u.full_name AS mentor_name, u.username AS mentor_username
            FROM cells c
            LEFT JOIN users u ON u.telegram_id = c.mentor_id
            WHERE c.direction_id = ?
            ORDER BY c.id
            """,
            (direction_id,),
        )
    else:
        cur = await conn.execute(
            """
            SELECT c.*, u.full_name AS mentor_name, u.username AS mentor_username
            FROM cells c
            LEFT JOIN users u ON u.telegram_id = c.mentor_id
            WHERE c.direction_id = ? AND c.is_active = 1
            ORDER BY c.id
            """,
            (direction_id,),
        )
    return list(await cur.fetchall())


async def _ensure_label_column(conn) -> None:
    cur = await conn.execute("PRAGMA table_info(cells)")
    columns = [row[1] for row in await cur.fetchall()]
    if "label" not in columns:
        await conn.execute("ALTER TABLE cells ADD COLUMN label TEXT")
        await conn.commit()


def cell_display_label(cell: aiosqlite.Row) -> str:
    """Preferred display label for a cell: custom label if set, else
    'Direction — Mentor' (or 'Direction — mentor yo'q' for peer-to-peer)."""
    keys = cell.keys()
    label = cell["label"] if "label" in keys else None
    if label:
        return label
    direction_name = cell["direction_name"] if "direction_name" in keys else ""
    mentor_name = cell["mentor_name"] if "mentor_name" in keys else None
    if mentor_name:
        return f"{direction_name} — {mentor_name}"
    return f"{direction_name} — mentor yo'q" if direction_name else f"Guruh #{cell['id']}"
