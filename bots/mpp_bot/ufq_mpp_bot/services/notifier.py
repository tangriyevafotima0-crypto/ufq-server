from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


def get_bot() -> Bot:
    if _bot is None:
        raise RuntimeError("Notifier bot instance is not set. Call set_bot() at startup.")
    return _bot


_bot_username: str | None = None


async def get_bot_username() -> str:
    global _bot_username
    if _bot_username is None:
        me = await get_bot().get_me()
        _bot_username = me.username
    return _bot_username


async def build_invite_link(cell_id: int) -> str:
    username = await get_bot_username()
    return f"https://t.me/{username}?start=join_{cell_id}"


async def safe_send(user_id: int, text: str, **kwargs) -> bool:
    """Send a message, swallowing delivery errors (blocked bot, deactivated user, etc.)."""
    try:
        await get_bot().send_message(user_id, text, **kwargs)
        return True
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning("Failed to deliver message to %s: %s", user_id, e)
        return False


async def notify_task_assigned(task_id: int, partners, title: str, description: str, deadline_db: str) -> list[dict]:
    """Notify partners about a new task. Returns the list of partners the bot
    could NOT reach (e.g. they never pressed /start), so the caller can warn
    the mentor instead of silently losing the notification.
    """
    from utils.timez import humanize

    text = (
        f"📌 Sizga yangi vazifa berildi!\n\n"
        f"<b>{title}</b>\n"
        f"{description or ''}\n"
        f"⏰ Muddat: {humanize(deadline_db)}"
    )
    unreachable = []
    for p in partners:
        delivered = await safe_send(p["telegram_id"], text)
        if not delivered:
            unreachable.append(p)
    return unreachable
