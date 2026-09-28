"""Bootstrap Phase A (IELTS track) using known real Telegram numeric IDs.

Usage:
    1. Fill in TELEGRAM_ID_MAP below with each person's real numeric Telegram
       ID (get it from @userinfobot or similar — do NOT use placeholders).
    2. Run: python -m scripts.seed_phase_a

Design notes (fixes from earlier revisions):
  - This script does NOT require anyone to have pressed /start first. It
    self-bootstraps every listed person straight into the `users` table via
    INSERT OR IGNORE using their real Telegram ID and a placeholder name that
    will be silently overwritten by the real full_name/username the moment
    they do press /start (UserSyncMiddleware's upsert always wins on
    full_name/username, keyed by the same telegram_id — so there is no
    lasting desync as long as the ID entered here is their real one).
  - Each mentor/partner assignment is attempted independently. If one person
    is missing or misconfigured, that single assignment is skipped with a
    clear message — the rest of the batch still completes. There is no
    all-or-nothing gate that can deadlock the whole script on one holdout.
"""
from __future__ import annotations

import asyncio

from database.db import init_db, close_db, get_conn
from database.repo_cells import CellError, add_partner, create_cell
from database.repo_directions import create_direction, direction_name_exists, get_direction, list_directions
from database.repo_users import get_user

DIRECTION_NAME = "IELTS"

# Fill these in with real Telegram numeric IDs before running. Leave as None
# for anyone not yet known — their assignments will simply be skipped (with
# a message) rather than blocking everyone else.
TELEGRAM_ID_MAP = {
    "Zafar": None,
    "Sultonali": None,
    "Sardor": None,
    "Firuza": None,
    "Bonu": None,
    "Asila": None,
    "Hayot": None,
    "Anora": None,
    "Malika": None,
}

# mentor_name -> [partner_names]
CELL_ASSIGNMENTS = {
    "Zafar": ["Firuza", "Bonu"],
    "Sultonali": ["Asila", "Hayot"],
    "Sardor": ["Anora", "Malika"],
}


async def _ensure_user_bootstrapped(telegram_id: int, display_name: str) -> None:
    """Create a minimal users row for telegram_id if it doesn't exist yet.

    Uses INSERT OR IGNORE so it never clobbers a real profile that already
    synced via /start (UserSyncMiddleware keeps full_name/username current
    from then on regardless of what placeholder we write here).
    """
    conn = get_conn()
    await conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, full_name, username) VALUES (?, ?, NULL)",
        (telegram_id, display_name),
    )
    await conn.commit()


async def main() -> None:
    await init_db()
    try:
        if not await direction_name_exists(DIRECTION_NAME):
            await create_direction(DIRECTION_NAME)
        directions = await list_directions()
        direction = next(d for d in directions if d["name"] == DIRECTION_NAME)

        # Self-bootstrap every known (non-None) ID straight into `users`, so
        # the script never depends on people having pressed /start first.
        for name, tg_id in TELEGRAM_ID_MAP.items():
            if tg_id is not None:
                await _ensure_user_bootstrapped(tg_id, name)

        for mentor_name, partner_names in CELL_ASSIGNMENTS.items():
            mentor_id = TELEGRAM_ID_MAP.get(mentor_name)
            if mentor_id is None:
                print(f"[{mentor_name}] o'tkazib yuborildi: Telegram ID hali kiritilmagan.")
                continue

            try:
                cell_id = await create_cell(direction["id"], mentor_id)
            except CellError as e:
                # Likely "already a mentor here" on a re-run — fetch the
                # existing cell so partner assignment can still proceed.
                print(f"[{mentor_name}] hujayra yaratilmadi ({e}); mavjud hujayra qidirilmoqda...")
                from database.repo_cells import list_cells_for_mentor

                existing = await list_cells_for_mentor(mentor_id)
                cell_id = next((c["id"] for c in existing if c["direction_id"] == direction["id"]), None)
                if cell_id is None:
                    print(f"[{mentor_name}] hujayra topilmadi, partnerlar qo'shilmaydi.")
                    continue

            for pname in partner_names:
                partner_id = TELEGRAM_ID_MAP.get(pname)
                if partner_id is None:
                    print(f"[{mentor_name}] partner {pname} o'tkazib yuborildi: Telegram ID hali kiritilmagan.")
                    continue
                try:
                    await add_partner(cell_id, partner_id)
                    print(f"[{mentor_name}] + partner {pname} qo'shildi.")
                except CellError as e:
                    print(f"[{mentor_name}] partner {pname} qo'shilmadi: {e}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
