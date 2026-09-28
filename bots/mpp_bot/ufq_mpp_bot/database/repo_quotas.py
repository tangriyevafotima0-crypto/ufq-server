"""
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
