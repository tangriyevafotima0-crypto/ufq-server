from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

# Every command actually registered with @router.message(Command(...)) or
# CommandStart() across the bot. Kept as an explicit allowlist (not a bare
# "starts with /" check) so free-text FSM input that happens to start with a
# slash — a task description like "/3-qism" or a path like "/materials/x.pdf" —
# is never mistaken for a command and doesn't wipe an in-progress flow.
REGISTERED_COMMANDS = {
    "start",
    "menu",
    "bekor",
    "partner_qosh",
    "kod_olish",
    "qoshilish",
    "partnerlarim",
    "vazifa_ber",
    "deadline_uzaytir",
    "mock_kirit",
    "holat",
    "statistika",
    "yonalishlar",
    "mentor_tayinlash",
    "admin_boshqaruv",
    "hisobot",
}

# Commands whose own handlers already manage state (clear it themselves or
# intentionally continue a flow) — excluded so we don't double-clear or race
# with their own logic.
_SELF_MANAGED = {"start", "menu", "bekor"}


class FSMGuardMiddleware(BaseMiddleware):
    """Prevents the 'FSM trap': if a user is mid-flow (e.g. /vazifa_ber waiting
    for a title) and fires an unrelated *registered* top-level command (e.g.
    /statistika), the stray state is cleared first so the new command's own
    handler runs normally instead of the old flow swallowing it as free-text
    input. Plain text that merely starts with '/' but isn't a real command is
    left untouched.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            command = event.text[1:].split()[0].split("@")[0].lower()
            if command in REGISTERED_COMMANDS and command not in _SELF_MANAGED:
                state: FSMContext | None = data.get("state")
                if state is not None and await state.get_state() is not None:
                    await state.clear()
        return await handler(event, data)
