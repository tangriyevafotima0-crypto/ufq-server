"""
handlers/mentor_zoom.py
--------------------------
Implements QOLGAN_ISHLAR.md section 2 (mentor side): schedule/edit/delete
Zoom sessions, view partner time suggestions/conflicts, and see the full
history/count in the group profile. Reminders (24h/3h/2h/1h) and the
post-session "did it happen?" check are wired in services/scheduler.py.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.repo_cells import list_cells_for_mentor
from database.repo_zoom import (
    create_zoom_session,
    delete_zoom_session,
    get_zoom_session,
    list_all_zoom_sessions_for_cell,
    list_unresolved_suggestions_for_cell,
    resolve_suggestions_for_cell,
    update_zoom_session_time,
)
from keyboards.dynamic_menu import (
    BTN_ZOOM_SCHEDULE_MANAGE,
    v2_cells_kb,
    zoom_delete_confirm_kb,
    zoom_manage_menu_kb,
    zoom_session_detail_kb,
    zoom_sessions_list_kb,
)
from middlewares.access import IsMentor
from services.notifier import safe_send
from services.scheduler import schedule_zoom_reminders_sync, unschedule_zoom_reminders
from utils.timez import TZ, now_tz
from utils.validators import validate_deadline_input

router = Router(name="mentor_zoom")
logger = logging.getLogger("ufq_mpp_bot")


class ZoomSchedule(StatesGroup):
    waiting_cell = State()
    waiting_datetime = State()
    waiting_note = State()
    waiting_edit_datetime = State()


async def _resolve_mentor_single_cell(message_or_cb, state: FSMContext):
    from_user = message_or_cb.from_user
    cells = await list_cells_for_mentor(from_user.id)
    if not cells:
        return None, cells
    if len(cells) == 1:
        return cells[0], cells
    return None, cells


@router.message(F.text == BTN_ZOOM_SCHEDULE_MANAGE, IsMentor())
async def btn_zoom_schedule_manage(message: Message, state: FSMContext) -> None:
    cell, cells = await _resolve_mentor_single_cell(message, state)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    if cell is None:
        await state.set_state(ZoomSchedule.waiting_cell)
        await message.answer("Qaysi guruh uchun?", reply_markup=v2_cells_kb(cells, "v2zoom_manage_cell"))
        return
    await state.update_data(cell_id=cell["id"])
    await message.answer("🎥 Zoom sanalari boshqaruvi:", reply_markup=zoom_manage_menu_kb())


@router.callback_query(ZoomSchedule.waiting_cell, F.data.startswith("v2zoom_manage_cell:"))
async def cb_zoom_manage_cell_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.clear()
    await state.update_data(cell_id=cell_id)
    await callback.message.answer("🎥 Zoom sanalari boshqaruvi:", reply_markup=zoom_manage_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "v2zoomdate_menu")
async def cb_zoomdate_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("🎥 Zoom sanalari boshqaruvi:", reply_markup=zoom_manage_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "v2zoomdate_list")
async def cb_zoomdate_list(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    sessions = await list_all_zoom_sessions_for_cell(cell_id) if cell_id else []
    if not sessions:
        await callback.message.answer("Hozircha Zoom sanasi belgilanmagan.")
        await callback.answer()
        return
    await callback.message.answer("Zoom darslari:", reply_markup=zoom_sessions_list_kb(sessions))
    await callback.answer()


@router.callback_query(F.data.startswith("v2zoomdate_open:"))
async def cb_zoomdate_open(callback: CallbackQuery) -> None:
    session_id = int(callback.data.split(":")[1])
    s = await get_zoom_session(session_id)
    if not s:
        await callback.answer("Topilmadi")
        return
    text = f"🎥 <b>Zoom dars</b>\n🕒 {s['session_at']}\n📝 {s['note'] or '—'}\n📌 Holat: {s['status']}"
    await callback.message.answer(text, reply_markup=zoom_session_detail_kb(session_id))
    await callback.answer()


@router.callback_query(F.data == "v2zoomdate_new")
async def cb_zoomdate_new(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ZoomSchedule.waiting_datetime)
    await callback.message.answer(
        "Zoom dars sanasi va vaqtini kiriting (format: YYYY-MM-DD HH:MM):"
    )
    await callback.answer()


@router.message(ZoomSchedule.waiting_datetime, F.text)
async def process_zoom_new_datetime(message: Message, state: FSMContext) -> None:
    ok, err = validate_deadline_input(message.text)
    if not ok:
        await message.answer(err)
        return
    await state.update_data(session_at=message.text.strip())
    await state.set_state(ZoomSchedule.waiting_note)
    await message.answer("Izoh qo'shmoqchimisiz? (ixtiyoriy, yo'q bo'lsa \"-\" yuboring)")


@router.message(ZoomSchedule.waiting_note, F.text)
async def process_zoom_new_note(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data["cell_id"]
    session_at = data["session_at"]
    note = None if message.text.strip() == "-" else message.text.strip()

    from datetime import datetime

    naive = datetime.strptime(session_at, "%Y-%m-%d %H:%M")
    dt = naive.replace(tzinfo=TZ)

    session_id = await create_zoom_session(cell_id, message.from_user.id, session_at, note)
    await resolve_suggestions_for_cell(cell_id, session_id)
    await schedule_zoom_reminders_sync(session_id, cell_id, dt)

    from database.repo_cells import list_cell_partners

    partners = await list_cell_partners(cell_id)
    for p in partners:
        await safe_send(
            p["telegram_id"],
            f"🎥 Yangi Zoom dars belgilandi: {session_at}" + (f"\n📝 {note}" if note else ""),
        )

    await state.clear()
    await state.update_data(cell_id=cell_id)
    await message.answer("✅ Zoom darsi belgilandi va sheriklarga xabar yuborildi.")


@router.callback_query(F.data.startswith("v2zoomdate_edit:"))
async def cb_zoomdate_edit(callback: CallbackQuery, state: FSMContext) -> None:
    session_id = int(callback.data.split(":")[1])
    await state.set_state(ZoomSchedule.waiting_edit_datetime)
    await state.update_data(edit_session_id=session_id)
    await callback.message.answer("Yangi sana/vaqtni kiriting (YYYY-MM-DD HH:MM):")
    await callback.answer()


@router.message(ZoomSchedule.waiting_edit_datetime, F.text)
async def process_zoom_edit(message: Message, state: FSMContext) -> None:
    ok, err = validate_deadline_input(message.text)
    if not ok:
        await message.answer(err)
        return
    data = await state.get_data()
    session_id = data["edit_session_id"]
    cell_id = data.get("cell_id")
    new_str = message.text.strip()

    from datetime import datetime

    naive = datetime.strptime(new_str, "%Y-%m-%d %H:%M")
    dt = naive.replace(tzinfo=TZ)

    await update_zoom_session_time(session_id, new_str)
    await schedule_zoom_reminders_sync(session_id, cell_id, dt)

    if cell_id:
        from database.repo_cells import list_cell_partners

        partners = await list_cell_partners(cell_id)
        for p in partners:
            await safe_send(p["telegram_id"], f"🔄 Zoom dars vaqti yangilandi: {new_str}")

    await state.clear()
    await state.update_data(cell_id=cell_id)
    await message.answer("✅ Zoom sanasi yangilandi.")


@router.callback_query(F.data.startswith("v2zoomdate_delete_confirm:"))
async def cb_zoomdate_delete_confirm(callback: CallbackQuery) -> None:
    session_id = int(callback.data.split(":")[1])
    await callback.message.answer("O'chirishni tasdiqlaysizmi?", reply_markup=zoom_delete_confirm_kb(session_id))
    await callback.answer()


@router.callback_query(F.data.startswith("v2zoomdate_delete_yes:"))
async def cb_zoomdate_delete_yes(callback: CallbackQuery) -> None:
    session_id = int(callback.data.split(":")[1])
    await unschedule_zoom_reminders(session_id)
    await delete_zoom_session(session_id)
    await callback.message.answer("🗑 Zoom darsi o'chirildi.")
    await callback.answer()


@router.callback_query(F.data == "v2zoomdate_suggestions")
async def cb_zoomdate_suggestions(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    rows = await list_unresolved_suggestions_for_cell(cell_id) if cell_id else []
    if not rows:
        await callback.message.answer("Hozircha yangi takliflar/e'tirozlar yo'q.")
        await callback.answer()
        return
    lines = ["💬 <b>Partner takliflari</b>"]
    for r in rows:
        kind_label = "⚠️ E'tiroz" if r["kind"] == "conflict" else "💡 Taklif"
        lines.append(f"\n{kind_label} — {r['full_name']}:\n{r['message']}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()
