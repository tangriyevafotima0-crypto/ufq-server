"""
handlers/partner_zoom_feedback.py
------------------------------------
Partner side of QOLGAN_ISHLAR.md section 2: leave a "bu vaqt mos kelmaydi" /
"menga qulay vaqt" note against their cell, view upcoming/past Zoom dates,
and answer the post-session "zoom o'tdimi?" check (fired by scheduler.py).
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.repo_cells import get_cells_for_partner
from database.repo_zoom import (
    add_time_suggestion,
    list_all_zoom_sessions_for_cell,
    list_upcoming_zoom_sessions_for_cell,
    set_confirmation,
)
from keyboards.dynamic_menu import BTN_CELL_ZOOM_DATES, v2_cells_kb
from services.notifier import safe_send
from utils.timez import now_tz

router = Router(name="partner_zoom_feedback")
logger = logging.getLogger("ufq_mpp_bot")


class ZoomSuggestion(StatesGroup):
    waiting_cell = State()
    waiting_kind = State()
    waiting_message = State()


class ZoomPostCheck(StatesGroup):
    waiting_no_reason = State()


@router.message(F.text == BTN_CELL_ZOOM_DATES)
async def btn_cell_zoom_dates(message: Message) -> None:
    uid = message.from_user.id
    cells = await get_cells_for_partner(uid)
    if not cells:
        await message.answer("Sizda hozircha faol guruh yo'q.")
        return
    lines = ["🎥 <b>Guruh Zoom sanalari</b>"]
    total = 0
    for cell in cells:
        sessions = await list_all_zoom_sessions_for_cell(cell["id"])
        total += len(sessions)
        lines.append(f"\n📚 <b>{cell['direction_name']}</b> — jami {len(sessions)} ta")
        for s in sessions[:5]:
            status_icon = {"scheduled": "🕒", "done": "✅", "cancelled": "❌"}.get(s["status"], "•")
            lines.append(f"  {status_icon} {s['session_at']}" + (f" — {s['note']}" if s["note"] else ""))
    await message.answer("\n".join(lines))

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for cell in cells:
        builder.button(text=f"💬 Taklif/E'tiroz — {cell['direction_name']}", callback_data=f"v2zoomsug_cell:{cell['id']}")
    builder.adjust(1)
    await message.answer("Vaqt mos kelmasa yoki taklif bo'lsa, mentorga yozib qoldiring:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("v2zoomsug_cell:"))
async def cb_zoom_suggestion_cell(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.set_state(ZoomSuggestion.waiting_kind)
    await state.update_data(cell_id=cell_id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Bu vaqt mos kelmaydi", callback_data="v2zoomsug_kind:conflict")
    builder.button(text="💡 Menga qulay vaqt", callback_data="v2zoomsug_kind:preference")
    builder.adjust(1)
    await callback.message.answer("Qaysi turdagi xabar?", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ZoomSuggestion.waiting_kind, F.data.startswith("v2zoomsug_kind:"))
async def cb_zoom_suggestion_kind(callback: CallbackQuery, state: FSMContext) -> None:
    kind = callback.data.split(":")[1]
    await state.update_data(kind=kind)
    await state.set_state(ZoomSuggestion.waiting_message)
    await callback.message.answer("Xabaringizni yozing:")
    await callback.answer()


@router.message(ZoomSuggestion.waiting_message, F.text)
async def process_zoom_suggestion_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await add_time_suggestion(data["cell_id"], message.from_user.id, data["kind"], message.text.strip())
    await state.clear()
    await message.answer("✅ Xabaringiz mentorga yetkaziladi.")


# ---------------------------------------------------------------------------
# Post-session "zoom o'tdimi?" response (button sent by scheduler.py)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("v2zoompost:"))
async def cb_zoom_post_response(callback: CallbackQuery, state: FSMContext) -> None:
    _, session_id_str, answer = callback.data.split(":")
    session_id = int(session_id_str)

    if answer == "yes":
        await set_confirmation(session_id, callback.from_user.id, "yes")
        await callback.message.edit_text(callback.message.text + "\n\n✅ Rahmat, javobingiz saqlandi.")
        await callback.answer()
        return

    await state.set_state(ZoomPostCheck.waiting_no_reason)
    await state.update_data(zoom_post_session_id=session_id)
    await callback.message.answer("Sababini qisqacha yozib qoldiring (mentor va admin ko'radi):")
    await callback.answer()


@router.message(ZoomPostCheck.waiting_no_reason, F.text)
async def process_zoom_post_no_reason(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = data["zoom_post_session_id"]
    reason = message.text.strip()
    await set_confirmation(session_id, message.from_user.id, "no", reason)
    await state.clear()
    await message.answer("✅ Qabul qilindi, tezroq o'tkazish uchun mentor va adminga xabar berildi.")

    from database.repo_zoom import get_zoom_session
    from database.repo_cells import list_cells_for_mentor
    from database.repo_users import get_user
    from config import config

    session = await get_zoom_session(session_id)
    if not session:
        return
    from database.repo_cells import list_cell_partners

    # Find the mentor of this cell to notify, plus all configured admins.
    from database.db import get_conn

    conn = get_conn()
    cur = await conn.execute("SELECT mentor_id FROM cells WHERE id = ?", (session["cell_id"],))
    row = await cur.fetchone()
    mentor_id = row["mentor_id"] if row else None

    user = await get_user(message.from_user.id)
    name = user["full_name"] if user else str(message.from_user.id)
    alert = f"⚠️ Zoom o'tmadi deb belgiladi: {name}\nSabab: {reason}\n🕒 {session['session_at']}"
    if mentor_id:
        await safe_send(mentor_id, alert)
    for admin_id in config.admin_ids:
        await safe_send(admin_id, alert)
