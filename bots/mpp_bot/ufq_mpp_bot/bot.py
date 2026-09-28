from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import close_db, init_db
from handlers import v2_panels
from handlers.v2_panels import on_any_error
from handlers import (
    admin_directions,
    admin_manage,
    admin_mentor,
    common,
    mentor_mock,
    mentor_partners,
    mentor_tasks,
    mentor_weekly_plan,
    mentor_zoom,
    partner_status,
    partner_zoom_feedback,
)
from middlewares.fsm_guard import FSMGuardMiddleware
from middlewares.user_sync import UserSyncMiddleware
from services.notifier import set_bot
from services.scheduler import reschedule_all_active_tasks_on_startup, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ufq_mpp_bot")


async def main() -> None:
    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    set_bot(bot)

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(UserSyncMiddleware())
    dp.message.middleware(FSMGuardMiddleware())
    dp.errors.register(on_any_error)

    dp.include_router(v2_panels.router)
    dp.include_router(mentor_weekly_plan.router)
    dp.include_router(mentor_zoom.router)
    dp.include_router(partner_zoom_feedback.router)
    dp.include_router(common.router)
    dp.include_router(admin_directions.router)
    dp.include_router(admin_mentor.router)
    dp.include_router(admin_manage.router)
    dp.include_router(mentor_partners.router)
    dp.include_router(mentor_tasks.router)
    dp.include_router(mentor_mock.router)
    dp.include_router(partner_status.router)

    start_scheduler()
    await reschedule_all_active_tasks_on_startup()

    logger.info("UFQ MPP Bot started. Timezone=%s", config.timezone)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
