from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from database.repo_cells import list_cells_for_mentor
from database.repo_users import is_admin


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return await is_admin(message.from_user.id)


class IsMentor(BaseFilter):
    """True if the user is a mentor of at least one active cell."""

    async def __call__(self, message: Message) -> bool:
        cells = await list_cells_for_mentor(message.from_user.id)
        return len(cells) > 0
