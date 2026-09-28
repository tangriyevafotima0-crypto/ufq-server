"""
handlers/mentor_weekly_plan.py
--------------------------------
Implements QOLGAN_ISHLAR.md section 1: mentor uploads a file (.docx/.txt) or
types the week's plan directly; the bot pattern-matches it into 7 days, or
falls back to AI reformatting (services/plan_parser.py) when the pattern
doesn't match. The resulting 7-day plan is distributed one day at a time to
every partner in the cell, with a Bajardim/Bajarmadim check-in button per
day, visible to partner/mentor/admin.

Registers its own router (mentor_weekly_plan.router), separate from
v2_panels.py's existing plain-text-only V2WeeklyPlan flow (BTN_UPLOAD_WEEKLY_PLAN),
which is left untouched for backward compatibility. This module adds the
richer BTN_WEEKLY_PLAN_MANAGE screen (view/edit/delete/new + per-day
check-ins + mentor confirmation) on top of it.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.repo_cells import list_cell_partners, list_cells_for_mentor
from database.repo_v2 import add_ledger_entry, create_weekly_plan
from database.repo_weekly_plan import (
    confirm_checkin_and_award,
    deactivate_previous_plans,
    delete_plan,
    ensure_checkin_rows,
    get_active_plan_for_cell,
    get_plan_day,
    insert_plan_day,
    list_checkins_for_plan_day,
    list_plan_days,
    list_unconfirmed_done_checkins_for_cell,
    mark_plan_day_distributed,
    set_checkin_status,
    set_source_meta,
)
from keyboards.dynamic_menu import (
    BTN_MY_WEEKLY_PLAN,
    BTN_WEEKLY_PLAN_MANAGE,
    plan_day_edit_pick_kb,
    plan_unconfirmed_kb,
    weekly_plan_day_checkin_kb,
    weekly_plan_delete_confirm_kb,
    weekly_plan_manage_menu_kb,
)
from keyboards.dynamic_menu import v2_cells_kb
from middlewares.access import IsMentor
from services.file_text_extract import extract_text_from_bytes
from services.notifier import safe_send
from services.plan_parser import parse_weekly_plan
from utils.timez import now_tz

router = Router(name="mentor_weekly_plan")
logger = logging.getLogger("ufq_mpp_bot")

CHECKIN_POINTS = 1


class WeeklyPlanUpload(StatesGroup):
    waiting_cell = State()
    waiting_file_or_text = State()


class WeeklyPlanEdit(StatesGroup):
    waiting_new_day_text = State()


async def _resolve_mentor_single_cell(message: Message, state: FSMContext):
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return None
    if len(cells) == 1:
        return cells[0]
    await state.set_state(WeeklyPlanUpload.waiting_cell)
    await message.answer("Qaysi guruh uchun?", reply_markup=v2_cells_kb(cells, "v2plan_upload_cell"))
    return None


# ---------------------------------------------------------------------------
# Upload entrypoint (mentor sends a file or types text directly)
# ---------------------------------------------------------------------------

@router.message(F.text == BTN_MY_WEEKLY_PLAN)
async def btn_my_weekly_plan(message: Message) -> None:
    """Partner-side: shows today's day of the active plan for each of their cells."""
    from database.repo_cells import get_cells_for_partner

    uid = message.from_user.id
    cells = await get_cells_for_partner(uid)
    if not cells:
        await message.answer("Sizda hozircha faol guruh yo'q.")
        return
    any_shown = False
    for cell in cells:
        plan = await get_active_plan_for_cell(cell["id"])
        if not plan:
            continue
        days = await list_plan_days(plan["id"])
        if not days:
            continue
        lines = [f"🗓 <b>{cell['direction_name']}</b> — haftalik reja"]
        for d in days:
            checkin = await get_plan_day(plan["id"], d["day_number"])
            lines.append(f"\n<b>{d['day_number']}-kun:</b> {d['content']}")
        await message.answer("\n".join(lines))
        any_shown = True
    if not any_shown:
        await message.answer("Hozircha sizga tayinlangan haftalik reja yo'q.")


@router.message(F.text == BTN_WEEKLY_PLAN_MANAGE, IsMentor())
async def btn_weekly_plan_manage(message: Message, state: FSMContext) -> None:
    cell = await _resolve_mentor_single_cell(message, state)
    if cell is None:
        return
    await state.update_data(cell_id=cell["id"])
    await message.answer("🗓 Haftalik reja boshqaruvi:", reply_markup=weekly_plan_manage_menu_kb())


@router.callback_query(WeeklyPlanUpload.waiting_cell, F.data.startswith("v2plan_upload_cell:"))
async def cb_plan_manage_cell_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await state.clear()
    await state.update_data(cell_id=cell_id)
    await callback.message.answer("🗓 Haftalik reja boshqaruvi:", reply_markup=weekly_plan_manage_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "v2plan_menu_back")
async def cb_plan_menu_back(callback: CallbackQuery) -> None:
    await callback.message.answer("🗓 Haftalik reja boshqaruvi:", reply_markup=weekly_plan_manage_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "v2plan_new")
async def cb_plan_new(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WeeklyPlanUpload.waiting_file_or_text)
    await callback.message.answer(
        "Kelgusi 7 kunlik reja faylini (.docx/.txt) yuboring, yoki matnini to'g'ridan-to'g'ri yozing.\n"
        "Format mos kelsa avtomatik aniqlanadi, aks holda AI yordamida qayta tuziladi."
    )
    await callback.answer()


@router.message(WeeklyPlanUpload.waiting_file_or_text, F.document)
async def process_plan_file(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    if cell_id is None:
        cell = await _resolve_mentor_single_cell(message, state)
        if cell is None:
            return
        cell_id = cell["id"]

    file = await message.bot.get_file(message.document.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    text = extract_text_from_bytes(file_bytes.read(), message.document.file_name)
    if not text.strip():
        await message.answer("Fayldan matn o'qib bo'lmadi. Iltimos matnli .docx yoki .txt yuboring.")
        return

    await _save_and_distribute_plan(message, cell_id, text, message.document.file_name)
    await state.clear()
    await state.update_data(cell_id=cell_id)


@router.message(WeeklyPlanUpload.waiting_file_or_text, F.text)
async def process_plan_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    if cell_id is None:
        cell = await _resolve_mentor_single_cell(message, state)
        if cell is None:
            return
        cell_id = cell["id"]
    await _save_and_distribute_plan(message, cell_id, message.text, None)
    await state.clear()
    await state.update_data(cell_id=cell_id)


async def _save_and_distribute_plan(message: Message, cell_id: int, raw_text: str, file_name: str | None) -> None:
    parsed = await parse_weekly_plan(raw_text)
    week_number = int(now_tz().strftime("%Y%V"))
    await deactivate_previous_plans(cell_id)
    plan_id = await create_weekly_plan(cell_id, message.from_user.id, week_number, raw_text)
    await set_source_meta(plan_id, file_name, parsed.method)

    partners = await list_cell_partners(cell_id)
    partner_ids = [p["telegram_id"] for p in partners]

    start_date = now_tz().date()
    for day_num in range(1, 8):
        content = parsed.days.get(day_num, "—")
        day_date = (start_date + timedelta(days=day_num - 1)).isoformat()
        plan_day_id = await insert_plan_day(plan_id, day_num, day_date, content, distributed=(day_num == 1))
        if partner_ids:
            await ensure_checkin_rows(plan_day_id, partner_ids)

    method_label = {
        "pattern": "✅ Format avtomatik aniqlandi.",
        "ai": "🤖 AI yordamida 7 kunga qayta tuzildi.",
        "fallback_split": "⚠️ Format aniqlanmadi, matn taxminan 7 kunga bo'lindi — tekshirib chiqing.",
    }.get(parsed.method, "")

    await message.answer(f"✅ Haftalik reja saqlandi va sheriklarga tarqatildi.\n{method_label}")

    # Day 1 is sent immediately; days 2-7 are auto-distributed daily by the
    # scheduler job in services/scheduler.py (_weekly_plan_daily_distribution),
    # matched by day_date, since each day now carries a real calendar date.
    day1 = await get_plan_day(plan_id, 1)
    if day1:
        for pid in partner_ids:
            checkin_kb = weekly_plan_day_checkin_kb(day1["id"])
            await safe_send(pid, f"🗓 <b>1-kun vazifasi:</b>\n{day1['content']}", reply_markup=checkin_kb)


@router.callback_query(F.data == "v2plan_view")
async def cb_plan_view(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    plan = await get_active_plan_for_cell(cell_id) if cell_id else None
    if not plan:
        await callback.message.answer("Hozircha faol reja yo'q.")
        await callback.answer()
        return
    days = await list_plan_days(plan["id"])
    lines = ["🗓 <b>Joriy haftalik reja</b>"]
    for d in days:
        checkins = await list_checkins_for_plan_day(d["id"])
        done = sum(1 for c in checkins if c["status"] == "bajardim")
        total = len(checkins)
        lines.append(f"\n<b>{d['day_number']}-kun:</b> {d['content']}\n   ✅ {done}/{total} bajardi")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "v2plan_edit")
async def cb_plan_edit(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    plan = await get_active_plan_for_cell(cell_id) if cell_id else None
    if not plan:
        await callback.message.answer("Hozircha faol reja yo'q.")
        await callback.answer()
        return
    days = await list_plan_days(plan["id"])
    await callback.message.answer("Qaysi kunni tahrirlaysiz?", reply_markup=plan_day_edit_pick_kb(days))
    await callback.answer()


@router.callback_query(F.data.startswith("v2plan_edit_day:"))
async def cb_plan_edit_day_pick(callback: CallbackQuery, state: FSMContext) -> None:
    plan_day_id = int(callback.data.split(":")[1])
    await state.set_state(WeeklyPlanEdit.waiting_new_day_text)
    await state.update_data(edit_plan_day_id=plan_day_id)
    await callback.message.answer("Yangi matnni yuboring:")
    await callback.answer()


@router.message(WeeklyPlanEdit.waiting_new_day_text, F.text)
async def process_plan_day_edit(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    plan_day_id = data["edit_plan_day_id"]
    from database.db import get_conn

    conn = get_conn()
    await conn.execute("UPDATE weekly_plan_days SET content = ? WHERE id = ?", (message.text.strip(), plan_day_id))
    await conn.commit()
    await state.clear()
    await message.answer("✅ Kun matni yangilandi.")


@router.callback_query(F.data == "v2plan_delete_confirm")
async def cb_plan_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Rostdan ham joriy rejani o'chirmoqchimisiz?", reply_markup=weekly_plan_delete_confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "v2plan_delete_yes")
async def cb_plan_delete_yes(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    plan = await get_active_plan_for_cell(cell_id) if cell_id else None
    if plan:
        await delete_plan(plan["id"])
        await callback.message.answer("🗑 Reja o'chirildi.")
    await callback.answer()


@router.callback_query(F.data == "v2plan_unconfirmed")
async def cb_plan_unconfirmed(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data.get("cell_id")
    if not cell_id:
        await callback.answer()
        return
    rows = await list_unconfirmed_done_checkins_for_cell(cell_id)
    if not rows:
        await callback.message.answer("Tasdiqlanmagan bajarilgan vazifalar yo'q.")
        await callback.answer()
        return
    await callback.message.answer("Tasdiqlash uchun tanlang:", reply_markup=plan_unconfirmed_kb(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("v2plan_confirm:"))
async def cb_plan_confirm(callback: CallbackQuery) -> None:
    plan_day_id = int(callback.data.split(":")[1])
    # find the user from the callback context isn't directly available here;
    # re-query unresolved rows for this plan_day to get user_id + award.
    from database.db import get_conn

    conn = get_conn()
    cur = await conn.execute(
        "SELECT user_id FROM weekly_plan_checkins WHERE plan_day_id = ? AND status = 'bajardim' AND mentor_confirmed = 0",
        (plan_day_id,),
    )
    row = await cur.fetchone()
    if row:
        user_id = row["user_id"]
        await confirm_checkin_and_award(plan_day_id, user_id, CHECKIN_POINTS)
        await add_ledger_entry(user_id, None, CHECKIN_POINTS, "weekly_plan_day_checkin")
        await callback.answer("Tasdiqlandi ✅")
        await callback.message.answer("✅ Ball qo'shildi.")
    else:
        await callback.answer("Topilmadi")


# ---------------------------------------------------------------------------
# Partner check-in button
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("v2plan_day_chk:"))
async def cb_plan_day_checkin(callback: CallbackQuery) -> None:
    _, plan_day_id_str, status = callback.data.split(":")
    plan_day_id = int(plan_day_id_str)
    await set_checkin_status(plan_day_id, callback.from_user.id, status)
    label = "✅ Bajardim deb belgilandi." if status == "bajardim" else "❌ Bajarmadim deb belgilandi."
    await callback.answer()
    await callback.message.edit_text(callback.message.text + f"\n\n{label}")
