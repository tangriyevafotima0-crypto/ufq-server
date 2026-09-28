from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from config import config
from database.repo_users import get_user, set_admin, upsert_user


class UserSyncMiddleware(BaseMiddleware):
    """Ensures every incoming update's sender exists in the users table,
    and promotes configured ADMIN_IDS to admin status idempotently."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None and not user.is_bot:
            full_name = user.full_name or user.first_name or "Foydalanuvchi"
            await upsert_user(user.id, full_name, user.username)
            if user.id in config.admin_ids:
                existing = await get_user(user.id)
                if existing and not existing["is_admin"]:
                    await set_admin(user.id, True)
        return await handler(event, data)
