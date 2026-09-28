from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database.repo_cells import get_cells_for_partner, list_cell_partners
from database.repo_tasks import (
    get_submission,
    list_active_tasks_for_partner,
    list_all_tasks_for_partner,
    list_submissions_for_task,
    update_submission_status,
)
from keyboards.inline import task_status_kb
from utils import texts
from utils.timez import humanize

router = Router(name="partner_status")


@router.message(Command("holat"))
@router.message(F.text == "📋 Holatim")
async def cmd_status(message: Message) -> None:
    await _send_status_list(message.from_user.id, message.answer)


async def _send_status_list(user_id: int, send) -> None:
    """Shared renderer for /holat, used both by the direct command and by the
    'Vazifalarimni ko'rish' button on a batched multi-task reminder — each
    task gets its own unambiguous status buttons here.
    """
    tasks = await list_active_tasks_for_partner(user_id)
    if not tasks:
        await send(texts.NO_ACTIVE_TASKS_PARTNER)
        return
    await send(texts.MY_STATUS_HEADER)
    for t in tasks:
        text = (
            f"📌 <b>{t['title']}</b>\n"
            f"📚 {t['direction_name']}\n"
            f"⏰ Muddat: {humanize(t['deadline'])}\n"
            f"Holat: {texts.STATUS_LABELS.get(t['my_status'], t['my_status'])}"
        )
        await send(text, reply_markup=task_status_kb(t["submission_id"], t["my_status"]))


@router.callback_query(F.data == "open_my_status")
async def cb_open_my_status(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_status_list(callback.from_user.id, callback.message.answer)


@router.callback_query(F.data.startswith("status:"))
async def cb_status_update(callback: CallbackQuery) -> None:
    await callback.answer()
    _, submission_id_str, new_status = callback.data.split(":")
    submission_id = int(submission_id_str)
    submission = await get_submission(submission_id)
    if submission is None or submission["user_id"] != callback.from_user.id:
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    if submission["status"] == new_status:
        # Same button pressed again (double-tap / stale keyboard) — nothing to change.
        return
    await update_submission_status(submission_id, new_status)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.message.answer(texts.TASK_STATUS_UPDATED.format(status=texts.STATUS_LABELS.get(new_status, new_status)))


@router.message(Command("statistika"))
@router.message(F.text == "📊 Statistikam")
async def cmd_statistics(message: Message) -> None:
    uid = message.from_user.id
    tasks = await list_all_tasks_for_partner(uid)
    cells = await get_cells_for_partner(uid)

    lines = [texts.STATS_HEADER]
    if not tasks:
        lines.append(texts.NO_ACTIVE_TASKS_PARTNER)
    else:
        for t in tasks:
            emoji = {"kutilmoqda": "⏳", "jarayonda": "🔄", "bajardi": "✅", "bajarmadi": "❌"}.get(t["my_status"], "•")
            lines.append(texts.STATS_ROW.format(
                status_emoji=emoji,
                title=t["title"],
                status=texts.STATUS_LABELS.get(t["my_status"], t["my_status"]),
            ))

    for cell in cells:
        partners = await list_cell_partners(cell["id"])
        if len(partners) <= 1:
            continue
        lines.append(texts.COMPARATIVE_HEADER)
        for p in partners:
            p_tasks = await list_all_tasks_for_partner(p["telegram_id"])
            total = len(p_tasks)
            completed = sum(1 for t in p_tasks if t["my_status"] == "bajardi")
            pct = (completed / total * 100) if total else 0
            marker = "👤" if p["telegram_id"] == uid else "•"
            lines.append(f"{marker} " + texts.COMPARATIVE_ROW.format(
                name=p["full_name"], completed=completed, total=total, pct=pct
            ))

    await message.answer("\n".join(lines))
