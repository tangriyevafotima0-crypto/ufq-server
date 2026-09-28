"""
handlers/v2_panels.py
----------------------
Router for the v2 dynamic-menu feature set: role-based main menu, the four
top-level panels (O'qish / Mentor / Admin / Guruhlar-Reyting), the 3-day
tasks_progress check-in (+1 point), mock score logging via mock_exams/
mock_scores (+2 points, +1 bonus for significant improvement), the public
groups/leaderboard directory, and the cross-cell quota checks from
database/repo_quotas.py.

This router is ADDITIVE. It does not remove or replace any v1 handler
(admin_directions, admin_mentor, admin_manage, mentor_partners,
mentor_tasks, mentor_mock, partner_status) -- those keep working exactly as
before via their own reply-keyboard text triggers. Several v2 admin/mentor
buttons intentionally delegate to the existing v1 flows (documented inline
below) rather than reimplementing already-working features.

Points policy implemented here (spec section 2):
    - 3-day task check-in, marked "Bajardim" before the cycle's deadline: +1
    - Mock exam participation (a score entered for the user): +2
    - Significant improvement on a mock (mentor confirms): +1 bonus
    - Not completed: 0 (no ledger row is written for failures/no-shows)
All points are written to scores_ledger (source of truth for leaderboard
and "Guruh balli" / group average) via database/repo_v2.add_ledger_entry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ErrorEvent, Message

from database.repo_cells import (
    get_cells_for_partner,
    list_cell_partners,
    list_cells_for_mentor,
)
from database.repo_directions import (
    create_direction,
    direction_name_exists,
    list_directions,
    set_direction_category,
)
from database.repo_misc import list_mock_results_for_user
from database.repo_quotas import (
    MAX_CELLS_AS_MENTOR,
    MAX_CELLS_AS_PARTNER,
    QuotaError,
    assert_can_become_mentor,
    assert_can_join_as_partner,
    count_active_cells_as_partner,
)
from database.repo_users import get_user, is_admin
from database.repo_v2 import (
    add_ledger_entry,
    archive_mock_exam,
    cell_average_points,
    count_mock_exams_in_month_for_cell,
    count_zoom_sessions_for_week,
    create_mock_exam,
    create_weekly_plan,
    delete_mock_exam,
    get_latest_weekly_plan,
    get_mock_exam,
    get_task_progress,
    list_all_mock_exams_for_cell,
    list_leaderboard,
    list_scores_for_mock,
    list_upcoming_mock_exams_for_cell,
    log_zoom_session,
    mark_mock_exam_finished,
    record_mock_score,
    sum_points_for_user,
    unarchive_mock_exam,
    update_mock_exam_description,
    upsert_task_progress,
)
from keyboards.dynamic_menu import (
    BTN_ADMIN_PANEL,
    BTN_CELL_MANAGEMENT,
    BTN_CELL_MOCK_DATES,
    BTN_CREATE_DIRECTION_V2,
    BTN_GROUPS_RATING,
    BTN_JOIN_BY_CODE,
    BTN_LEADERBOARD,
    BTN_MAIN_MENU,
    BTN_MENTOR_PANEL,
    BTN_MOCK_DATE_SCHEDULE,
    BTN_MOCK_MANAGEMENT,
    BTN_MONTHLY_EXCEL,
    BTN_MY_GROUP,
    BTN_MY_PARTNERS_MENTOR,
    BTN_MY_RESULTS,
    BTN_MY_TASKS,
    BTN_OPEN_CELL_ASSIGN,
    BTN_STUDY_PANEL,
    BTN_UPLOAD_WEEKLY_PLAN,
    BTN_ZOOM_STATUS,
    admin_panel_v2_kb,
    direction_category_kb,
    groups_rating_kb,
    main_menu_kb,
    mentor_panel_kb,
    mock_score_significant_gain_kb,
    study_panel_kb,
    task_checkin_kb,
    v2_cells_kb,
    v2_mock_date_delete_confirm_kb,
    v2_mock_date_detail_kb,
    v2_mock_dates_list_kb,
    v2_mock_exams_kb,
    v2_mock_management_menu_kb,
    v2_partners_kb,
)
from keyboards.reply import remove_kb
from middlewares.access import IsMentor
from utils.timez import now_tz
from utils.validators import validate_score_input

router = Router(name="v2_panels")
logger = logging.getLogger("ufq_mpp_bot")


# ---------------------------------------------------------------------------
# FSM states (kept local to this router; does not touch handlers/states.py)
# ---------------------------------------------------------------------------

class V2DirectionCreation(StatesGroup):
    waiting_name = State()
    waiting_category = State()


class V2WeeklyPlan(StatesGroup):
    waiting_cell = State()
    waiting_text = State()


class V2MockManage(StatesGroup):
    waiting_cell_for_create = State()
    waiting_date_for_create = State()
    waiting_description_for_create = State()
    waiting_mock_for_score = State()
    waiting_partner_for_score = State()
    waiting_score_value = State()


class V2MockDateSchedule(StatesGroup):
    waiting_cell = State()
    waiting_date = State()
    waiting_note = State()
    waiting_edit_date = State()


# ---------------------------------------------------------------------------
# Role helpers / main-menu rendering
# ---------------------------------------------------------------------------

async def _roles(user_id: int) -> tuple[bool, bool, bool]:
    """Returns (is_admin, is_mentor, is_partner)."""
    admin = await is_admin(user_id)
    mentor_cells = await list_cells_for_mentor(user_id)
    partner_cells = await get_cells_for_partner(user_id)
    return admin, len(mentor_cells) > 0, len(partner_cells) > 0


async def send_main_menu(message: Message) -> None:
    admin, mentor, partner = await _roles(message.from_user.id)
    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_kb(is_admin=admin, is_mentor=mentor, is_partner=partner),
    )


@router.message(Command("v2menu"))
async def cmd_v2_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_main_menu(message)


@router.message(F.text == BTN_MAIN_MENU)
async def btn_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_main_menu(message)


# ---------------------------------------------------------------------------
# 📚 O'qish paneli (partner)
# ---------------------------------------------------------------------------

@router.message(F.text == BTN_STUDY_PANEL)
async def btn_study_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id
    cells_as_partner = await count_active_cells_as_partner(uid)
    show_join = cells_as_partner < MAX_CELLS_AS_PARTNER
    await message.answer("📚 O'qish paneli:", reply_markup=study_panel_kb(show_join_by_code=show_join))


@router.message(F.text == BTN_MY_PARTNERS_MENTOR)
async def btn_my_partners_and_mentor(message: Message) -> None:
    uid = message.from_user.id
    cells = await get_cells_for_partner(uid)
    if not cells:
        await message.answer("Siz hozircha hech qanday guruhga a'zo emassiz.")
        return
    lines = ["👥 <b>Sheriklarim va Mentorim</b>"]
    for cell in cells:
        lines.append(f"\n📚 <b>{cell['direction_name']}</b>")
        mentor_name = cell["mentor_name"] if "mentor_name" in cell.keys() else None
        lines.append(f"🎓 Mentor: {mentor_name}" if mentor_name else "🎓 Mentor: yo'q (tengdoshlar guruhi)")
        partners = await list_cell_partners(cell["id"])
        others = [p for p in partners if p["telegram_id"] != uid]
        if others:
            lines.append("🤝 Sheriklar:")
            for p in others:
                uname = f" (@{p['username']})" if p["username"] else ""
                lines.append(f"  • {p['full_name']}{uname}")
        else:
            lines.append("🤝 Sheriklar: hozircha yo'q")
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_MY_TASKS)
async def btn_my_tasks(message: Message) -> None:
    """Shows today's 3-day-cycle check-in card(s) for every cell the user is
    an active partner in. cycle_date is the current Asia/Tashkent date; the
    same progress_key (cell_id:cycle_date) is reused if the user re-opens
    this before checking in, so re-tapping doesn't create duplicate rows
    (tasks_progress has a UNIQUE(cell_id, user_id, cycle_date) upsert)."""
    uid = message.from_user.id
    cells = await get_cells_for_partner(uid)
    if not cells:
        await message.answer("Sizda hozircha faol guruh yo'q, shuning uchun vazifalar ham yo'q.")
        return
    today_str = now_tz().strftime("%Y-%m-%d")
    for cell in cells:
        existing = await get_task_progress(cell["id"], uid, today_str)
        text = (
            f"📋 <b>{cell['direction_name']}</b> — 3 kunlik vazifa tekshiruvi\n"
            f"Sana: {today_str}\n\n"
        )
        if existing is not None:
            status_label = "✅ Bajardim" if existing["is_completed"] else "❌ Bajarmadim"
            text += f"Bu davr uchun allaqachon belgilangansiz: {status_label}\nQayta belgilash shart emas."
            await message.answer(text)
            continue
        progress_key = f"{cell['id']}:{today_str}"
        text += "Ushbu davr uchun vazifangizni bajardingizmi?"
        await message.answer(text, reply_markup=task_checkin_kb(progress_key))


@router.callback_query(F.data.startswith("v2chk:"))
async def cb_task_checkin(callback: CallbackQuery) -> None:
    await callback.answer()
    _, cell_id_str, cycle_date, action = callback.data.split(":")
    cell_id = int(cell_id_str)
    uid = callback.from_user.id

    existing = await get_task_progress(cell_id, uid, cycle_date)
    if existing is not None:
        # Already checked in for this cycle (stale keyboard / double-tap) —
        # do nothing further, never re-ask or re-award points.
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    status_map = {"done": (True, 1), "progress": (False, 0), "failed": (False, 0)}
    is_completed, points = status_map.get(action, (False, 0))

    if action == "progress":
        # "Jarayonda" is not final — allow the card to remain actionable,
        # but don't write a terminal progress row that would block re-checkin.
        await callback.message.answer("⏳ Jarayonda deb belgilandi. Yakunlaganingizda qayta belgilang.")
        return

    await upsert_task_progress(cell_id, uid, cycle_date, is_completed, points)
    if action == "done":
        await add_ledger_entry(uid, cell_id, 1, f"3 kunlik vazifa ({cycle_date})")
        label = "✅ Bajardingiz! +1 ball qo'shildi."
    else:
        label = "❌ Bajarilmadi deb belgilandi. 0 ball."

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(label)


@router.message(F.text == BTN_CELL_MOCK_DATES)
async def btn_cell_mock_dates(message: Message) -> None:
    uid = message.from_user.id
    cells = await get_cells_for_partner(uid)
    if not cells:
        await message.answer("Sizda hozircha faol guruh yo'q.")
        return
    lines = ["🎯 <b>Guruh Mock sanalari</b>"]
    any_found = False
    for cell in cells:
        mocks = await list_upcoming_mock_exams_for_cell(cell["id"])
        if not mocks:
            continue
        any_found = True
        lines.append(f"\n📚 {cell['direction_name']}:")
        for m in mocks:
            label = await _mock_label_for_row(m)
            desc = f" — {m['description']}" if m["description"] else ""
            lines.append(f"  • <b>{label}</b>\n    🕐 {m['exam_date']}{desc}")
    if not any_found:
        lines.append("Hozircha rejalashtirilgan mock sanalar yo'q.")
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_MY_RESULTS)
async def btn_my_results(message: Message) -> None:
    uid = message.from_user.id
    total_points = await sum_points_for_user(uid)
    mock_results = await list_mock_results_for_user(uid)
    lines = [
        "📊 <b>Shaxsiy natijam</b>",
        f"🏆 Jami ball: {total_points}",
    ]
    if mock_results:
        lines.append("\n🎯 Mock natijalarim:")
        for r in mock_results[-5:]:
            lines.append(f"  • {r['direction_name']}: {r['score']} ({r['date']})")
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_JOIN_BY_CODE)
async def btn_join_by_code(message: Message) -> None:
    """Delegates to the existing, already-working invite-code flow.
    handlers/mentor_partners.py's JoinByCode FSM (triggered by /qoshilish or
    its own text button) already implements this end-to-end including
    quota-safe insertion via repo_cells.add_partner. We only guard here so
    the v2 study panel doesn't show a button that then silently fails the
    quota check without explanation.
    """
    uid = message.from_user.id
    current = await count_active_cells_as_partner(uid)
    if current >= MAX_CELLS_AS_PARTNER:
        await message.answer(
            f"❌ Siz allaqachon {MAX_CELLS_AS_PARTNER} ta guruhda partnersiz. "
            f"Yangisiga qo'shilishdan oldin birontasidan chiqishingiz kerak."
        )
        return
    await message.answer(
        "Hujayraga qo'shilish uchun kodni yuboring:\n<code>/qoshilish 123456</code>"
    )


# ---------------------------------------------------------------------------
# 🎓 Mentor paneli
# ---------------------------------------------------------------------------

@router.message(F.text == BTN_MENTOR_PANEL, IsMentor())
async def btn_mentor_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🎓 Mentor paneli:", reply_markup=mentor_panel_kb())


@router.message(F.text == BTN_UPLOAD_WEEKLY_PLAN, IsMentor())
async def btn_upload_weekly_plan(message: Message, state: FSMContext) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    if len(cells) == 1:
        await state.update_data(cell_id=cells[0]["id"])
        await state.set_state(V2WeeklyPlan.waiting_text)
        await message.answer(
            "Kelgusi 7 kunlik reja matnini yuboring (har kun uchun bitta qator tavsiya etiladi):"
        )
        return
    await state.set_state(V2WeeklyPlan.waiting_cell)
    await message.answer("Qaysi guruh uchun reja yuklamoqchisiz?", reply_markup=v2_cells_kb(cells, "v2plan_cell"))


@router.callback_query(V2WeeklyPlan.waiting_cell, F.data.startswith("v2plan_cell:"))
async def cb_weekly_plan_cell(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await state.set_state(V2WeeklyPlan.waiting_text)
    await callback.message.answer("Kelgusi 7 kunlik reja matnini yuboring:")
    await callback.answer()


@router.message(V2WeeklyPlan.waiting_text, F.text)
async def process_weekly_plan_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data["cell_id"]
    week_number = int(now_tz().strftime("%Y%V"))  # ISO year+week, monotonically increasing
    await create_weekly_plan(cell_id, message.from_user.id, week_number, message.text.strip())
    await state.clear()
    await message.answer("✅ 7 kunlik reja saqlandi va partnerlarga kunlik tarqatish uchun navbatga qo'yildi.")


@router.message(F.text == BTN_ZOOM_STATUS, IsMentor())
async def btn_zoom_status(message: Message) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    week_number = int(now_tz().strftime("%Y%V"))
    lines = ["📹 <b>Zoom dars holati</b> (joriy hafta)"]
    for cell in cells:
        cnt = await count_zoom_sessions_for_week(cell["id"], week_number)
        lines.append(f"• {cell['direction_name']}: {cnt} ta dars belgilangan")
    await message.answer("\n".join(lines))
    if len(cells) == 1:
        await log_zoom_session(cells[0]["id"], message.from_user.id, week_number)
        await message.answer(f"✅ '{cells[0]['direction_name']}' uchun bugungi Zoom darsi belgilandi.")
    else:
        await message.answer(
            "Zoom darsini belgilash uchun guruhni tanlang:",
            reply_markup=v2_cells_kb(cells, "v2zoom_mark"),
        )


@router.callback_query(F.data.startswith("v2zoom_mark:"))
async def cb_zoom_mark(callback: CallbackQuery) -> None:
    cell_id = int(callback.data.split(":")[1])
    week_number = int(now_tz().strftime("%Y%V"))
    await log_zoom_session(cell_id, callback.from_user.id, week_number)
    await callback.answer("Belgilandi ✅", show_alert=False)
    await callback.message.answer("✅ Zoom darsi belgilandi.")


@router.message(F.text == BTN_MOCK_MANAGEMENT, IsMentor())
async def btn_mock_management(message: Message, state: FSMContext) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    await state.set_state(V2MockManage.waiting_cell_for_create)
    await message.answer(
        "Mock imtihoni rejalashtirish uchun guruhni tanlang:",
        reply_markup=v2_cells_kb(cells, "v2mock_cell"),
    )


@router.callback_query(V2MockManage.waiting_cell_for_create, F.data.startswith("v2mock_cell:"))
async def cb_mock_cell(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await state.set_state(V2MockManage.waiting_date_for_create)
    await callback.message.answer("Mock sanasini kiriting (format: YYYY-MM-DD HH:MM):")
    await callback.answer()


@router.message(V2MockManage.waiting_date_for_create, F.text)
async def process_mock_date_create(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    try:
        datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Format noto'g'ri. Masalan: 2026-09-20 10:00")
        return
    await state.update_data(exam_date=raw)
    await state.set_state(V2MockManage.waiting_description_for_create)
    await message.answer("Tavsif kiriting (yoki \"-\"):")


@router.message(V2MockManage.waiting_description_for_create, F.text)
async def process_mock_description_create(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    description = None if message.text.strip() == "-" else message.text.strip()
    mock_id = await create_mock_exam(data["cell_id"], message.from_user.id, data["exam_date"], description)
    await state.clear()
    await message.answer(f"✅ Mock rejalashtirildi (ID: {mock_id}, sana: {data['exam_date']}).")


@router.message(Command("mock_ball"), IsMentor())
async def cmd_mock_ball(message: Message, state: FSMContext) -> None:
    """Enter a mock score for a partner: +2 for participating, and asks the
    mentor whether it's a significant improvement for the +1 bonus."""
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    all_mocks = []
    for c in cells:
        all_mocks.extend(await list_upcoming_mock_exams_for_cell(c["id"]))
    if not all_mocks:
        await message.answer("Hozircha rejalashtirilgan mock yo'q. Avval 🎯 Mock boshqaruvi orqali sana kiriting.")
        return
    await state.set_state(V2MockManage.waiting_mock_for_score)
    await message.answer("Qaysi mock uchun ball kiritmoqchisiz?", reply_markup=v2_mock_exams_kb(all_mocks, "v2mockscore_pick"))


@router.callback_query(V2MockManage.waiting_mock_for_score, F.data.startswith("v2mockscore_pick:"))
async def cb_mock_score_pick(callback: CallbackQuery, state: FSMContext) -> None:
    mock_id = int(callback.data.split(":")[1])
    mock = await get_mock_exam(mock_id)
    if mock is None:
        await callback.answer("Mock topilmadi.", show_alert=True)
        return
    partners = await list_cell_partners(mock["cell_id"])
    if not partners:
        await callback.message.answer("Bu guruhda partner yo'q.")
        await state.clear()
        await callback.answer()
        return
    await state.update_data(mock_id=mock_id)
    await state.set_state(V2MockManage.waiting_partner_for_score)
    await callback.message.answer("Qaysi partner uchun ball kiritmoqchisiz?", reply_markup=v2_partners_kb(partners, "v2mockscore_partner"))
    await callback.answer()


@router.callback_query(V2MockManage.waiting_partner_for_score, F.data.startswith("v2mockscore_partner:"))
async def cb_mock_score_partner(callback: CallbackQuery, state: FSMContext) -> None:
    partner_id = int(callback.data.split(":")[1])
    await state.update_data(partner_id=partner_id)
    await state.set_state(V2MockManage.waiting_score_value)
    await callback.message.answer("Natijani kiriting (masalan: 6.5):")
    await callback.answer()


@router.message(V2MockManage.waiting_score_value, F.text)
async def process_mock_score_value(message: Message, state: FSMContext) -> None:
    ok, err, score = validate_score_input(message.text)
    if not ok:
        await message.answer(err)
        return
    data = await state.get_data()
    mock_id = data["mock_id"]
    partner_id = data["partner_id"]

    # +2 for participating (submitting a result at all)
    await record_mock_score(mock_id, partner_id, score, points_awarded=2, entered_by=message.from_user.id)
    await add_ledger_entry(partner_id, None, 2, f"Mock qatnashish (mock #{mock_id})")

    partner = await get_user(partner_id)
    await state.clear()
    await message.answer(
        f"✅ Natija saqlandi: {partner['full_name']} — {score} ball. +2 ball berildi.\n\n"
        f"Sezilarli o'sish bormi? (bonus +1 ball uchun)",
        reply_markup=mock_score_significant_gain_kb(mock_id, partner_id),
    )


@router.callback_query(F.data.startswith("mockgain:"))
async def cb_mock_significant_gain(callback: CallbackQuery) -> None:
    _, mock_id_str, user_id_str, answer = callback.data.split(":")
    mock_id, user_id = int(mock_id_str), int(user_id_str)
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if answer == "yes":
        # Look up the score row we just wrote (rather than re-deriving it)
        # so the existing score_raw is preserved exactly when we bump
        # points_awarded from 2 to 3.
        scores = await list_scores_for_mock(mock_id)
        existing = next((s for s in scores if s["user_id"] == user_id), None)
        score_raw = existing["score_raw"] if existing else 0.0
        await add_ledger_entry(user_id, None, 1, f"Mock sezilarli o'sish bonusi (mock #{mock_id})")
        await record_mock_score(mock_id, user_id, score_raw, points_awarded=3, entered_by=callback.from_user.id)
        await callback.message.answer("🌟 +1 bonus ball qo'shildi (jami: +3 ball ushbu mock uchun).")
    else:
        await callback.message.answer("Tushunarli, bonus berilmadi.")


def _mock_auto_label(exam_date_str: str, ordinal: int) -> str:
    """'Sentyabr oyining 2-chi mocki' style auto-name from the exam date and
    its 1-based position among that cell's mocks in that calendar month."""
    from utils.timez import uz_month_name

    dt = datetime.strptime(exam_date_str, "%Y-%m-%d %H:%M")
    return f"{uz_month_name(dt)} oyining {ordinal}-chi mocki"


async def _mock_label_for_row(m) -> str:
    cell_id = m["cell_id"]
    exam_date = m["exam_date"]
    dt = datetime.strptime(exam_date, "%Y-%m-%d %H:%M")
    all_mocks = await list_all_mock_exams_for_cell(cell_id, include_archived=True)
    same_month = [
        x for x in all_mocks
        if datetime.strptime(x["exam_date"], "%Y-%m-%d %H:%M").year == dt.year
        and datetime.strptime(x["exam_date"], "%Y-%m-%d %H:%M").month == dt.month
    ]
    same_month.sort(key=lambda x: x["exam_date"])
    ordinal = next((i + 1 for i, x in enumerate(same_month) if x["id"] == m["id"]), 1)
    return _mock_auto_label(exam_date, ordinal)


@router.message(F.text == BTN_MOCK_DATE_SCHEDULE, IsMentor())
async def btn_mock_date_schedule(message: Message, state: FSMContext) -> None:
    await state.clear()
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    if len(cells) == 1:
        await state.update_data(cell_id=cells[0]["id"])
    else:
        await state.update_data(cell_id=None)
    await message.answer(
        "📅 <b>Mock sanasini belgilash</b>\n\n"
        "Bu yerda kelgusi mocklarni oldindan rejalashtirishingiz mumkin. "
        "Har bir mock avtomatik ravishda oy va shu oydagi tartib raqami bilan nomlanadi "
        "(masalan: \"Sentyabr oyining 2-chi mocki\").",
        reply_markup=v2_mock_management_menu_kb(),
    )


async def _resolve_mentor_cell(message_or_cb, state: FSMContext):
    data = await state.get_data()
    cell_id = data.get("cell_id")
    uid = message_or_cb.from_user.id
    cells = await list_cells_for_mentor(uid)
    if cell_id and any(c["id"] == cell_id for c in cells):
        return cell_id, cells
    return None, cells


@router.callback_query(F.data == "v2mockdate_menu")
async def cb_mockdate_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("📅 Mock sanasini belgilash:", reply_markup=v2_mock_management_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "v2mockdate_list")
async def cb_mockdate_list(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id, cells = await _resolve_mentor_cell(callback, state)
    if cell_id is None and len(cells) > 1:
        await callback.message.answer("Qaysi guruh uchun?", reply_markup=v2_cells_kb(cells, "v2mockdate_cell"))
        await callback.answer()
        return
    if cell_id is None:
        await callback.answer("Sizga biriktirilgan faol guruh yo'q.", show_alert=True)
        return
    mocks = await list_all_mock_exams_for_cell(cell_id, include_archived=False)
    if not mocks:
        await callback.message.answer("Hozircha rejalashtirilgan mock sana yo'q.", reply_markup=v2_mock_management_menu_kb())
        await callback.answer()
        return
    labeled = []
    for m in mocks:
        label = await _mock_label_for_row(m)
        labeled.append({**dict(m), "auto_label": label})
    await callback.message.answer("📅 Faol mock sanalari:", reply_markup=v2_mock_dates_list_kb(labeled))
    await callback.answer()


@router.callback_query(F.data == "v2mockdate_archive_list")
async def cb_mockdate_archive_list(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id, cells = await _resolve_mentor_cell(callback, state)
    if cell_id is None and len(cells) > 1:
        await callback.message.answer("Qaysi guruh uchun?", reply_markup=v2_cells_kb(cells, "v2mockdate_cell_arch"))
        await callback.answer()
        return
    if cell_id is None:
        await callback.answer("Sizga biriktirilgan faol guruh yo'q.", show_alert=True)
        return
    all_mocks = await list_all_mock_exams_for_cell(cell_id, include_archived=True)
    archived = [m for m in all_mocks if m["is_archived"]]
    if not archived:
        await callback.message.answer("Arxivda hech narsa yo'q.", reply_markup=v2_mock_management_menu_kb())
        await callback.answer()
        return
    labeled = []
    for m in archived:
        label = await _mock_label_for_row(m)
        labeled.append({**dict(m), "auto_label": label + " (arxiv)"})
    await callback.message.answer("🗄 Arxivlangan mock sanalar:", reply_markup=v2_mock_dates_list_kb(labeled, archived=True))
    await callback.answer()


@router.callback_query(F.data.startswith("v2mockdate_cell:"))
async def cb_mockdate_pick_cell_for_list(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await cb_mockdate_list(callback, state)


@router.callback_query(F.data.startswith("v2mockdate_cell_arch:"))
async def cb_mockdate_pick_cell_for_archive_list(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await cb_mockdate_archive_list(callback, state)


@router.callback_query(F.data == "v2mockdate_new")
async def cb_mockdate_new(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id, cells = await _resolve_mentor_cell(callback, state)
    if cell_id is None and len(cells) > 1:
        await state.set_state(V2MockDateSchedule.waiting_cell)
        await callback.message.answer("Qaysi guruh uchun mock sana qo'shmoqchisiz?", reply_markup=v2_cells_kb(cells, "v2mockdate_new_cell"))
        await callback.answer()
        return
    if cell_id is None:
        await callback.answer("Sizga biriktirilgan faol guruh yo'q.", show_alert=True)
        return
    await state.update_data(cell_id=cell_id)
    await state.set_state(V2MockDateSchedule.waiting_date)
    await callback.message.answer("Mock sanasini kiriting (format: YYYY-MM-DD HH:MM):")
    await callback.answer()


@router.callback_query(V2MockDateSchedule.waiting_cell, F.data.startswith("v2mockdate_new_cell:"))
async def cb_mockdate_new_cell_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await state.set_state(V2MockDateSchedule.waiting_date)
    await callback.message.answer("Mock sanasini kiriting (format: YYYY-MM-DD HH:MM):")
    await callback.answer()


@router.message(V2MockDateSchedule.waiting_date, F.text)
async def process_mockdate_new_date(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    try:
        datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Format noto'g'ri. Masalan: 2026-09-20 10:00")
        return
    await state.update_data(exam_date=raw)
    await state.set_state(V2MockDateSchedule.waiting_note)
    await message.answer("Qo'shimcha izoh kiriting (yoki \"-\"):")


@router.message(V2MockDateSchedule.waiting_note, F.text)
async def process_mockdate_new_note(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    description = None if message.text.strip() == "-" else message.text.strip()
    cell_id = data["cell_id"]
    exam_date = data["exam_date"]
    mock_id = await create_mock_exam(cell_id, message.from_user.id, exam_date, description)
    dt = datetime.strptime(exam_date, "%Y-%m-%d %H:%M")
    ordinal = await count_mock_exams_in_month_for_cell(cell_id, dt.year, dt.month)
    label = _mock_auto_label(exam_date, ordinal)
    await state.clear()
    await message.answer(
        f"✅ Mock rejalashtirildi: <b>{label}</b>\n🕐 Sana: {exam_date}\n"
        f"Bu sana guruh profilida admin, mentor va partnerlarga doimiy ko'rinadi."
    )


@router.callback_query(F.data.startswith("v2mockdate_open:"))
async def cb_mockdate_open(callback: CallbackQuery) -> None:
    mock_id = int(callback.data.split(":")[1])
    mock = await get_mock_exam(mock_id)
    if mock is None:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    label = await _mock_label_for_row(mock)
    text = (
        f"📅 <b>{label}</b>\n"
        f"🕐 Sana: {mock['exam_date']}\n"
        f"📝 Izoh: {mock['description'] or '—'}\n"
        f"Holat: {'🗄 Arxivlangan' if mock['is_archived'] else '✅ Faol'}"
    )
    await callback.message.answer(text, reply_markup=v2_mock_date_detail_kb(mock_id, bool(mock["is_archived"])))
    await callback.answer()


@router.callback_query(F.data.startswith("v2mockdate_archive:"))
async def cb_mockdate_archive(callback: CallbackQuery) -> None:
    mock_id = int(callback.data.split(":")[1])
    await archive_mock_exam(mock_id)
    await callback.answer("Arxivlandi ✅")
    await callback.message.answer("🗄 Mock sana arxivlandi.", reply_markup=v2_mock_management_menu_kb())


@router.callback_query(F.data.startswith("v2mockdate_unarchive:"))
async def cb_mockdate_unarchive(callback: CallbackQuery) -> None:
    mock_id = int(callback.data.split(":")[1])
    await unarchive_mock_exam(mock_id)
    await callback.answer("Arxivdan chiqarildi ✅")
    await callback.message.answer("♻️ Mock sana arxivdan chiqarildi.", reply_markup=v2_mock_management_menu_kb())


@router.callback_query(F.data.startswith("v2mockdate_delete_confirm:"))
async def cb_mockdate_delete_confirm(callback: CallbackQuery) -> None:
    mock_id = int(callback.data.split(":")[1])
    await callback.message.answer(
        "⚠️ Ushbu mock sanasini butunlay o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.",
        reply_markup=v2_mock_date_delete_confirm_kb(mock_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("v2mockdate_delete_yes:"))
async def cb_mockdate_delete_yes(callback: CallbackQuery) -> None:
    mock_id = int(callback.data.split(":")[1])
    await delete_mock_exam(mock_id)
    await callback.answer("O'chirildi.")
    await callback.message.answer("🗑 Mock sana o'chirildi.", reply_markup=v2_mock_management_menu_kb())


@router.callback_query(F.data.startswith("v2mockdate_edit:"))
async def cb_mockdate_edit(callback: CallbackQuery, state: FSMContext) -> None:
    mock_id = int(callback.data.split(":")[1])
    await state.update_data(edit_mock_id=mock_id)
    await state.set_state(V2MockDateSchedule.waiting_edit_date)
    await callback.message.answer(
        "Yangi sana va vaqtni kiriting (format: YYYY-MM-DD HH:MM), yoki izohni o'zgartirish uchun "
        "\"izoh: matn\" ko'rinishida yozing:"
    )
    await callback.answer()


@router.message(V2MockDateSchedule.waiting_edit_date, F.text)
async def process_mockdate_edit(message: Message, state: FSMContext) -> None:
    from database.repo_v2 import update_mock_exam_date

    data = await state.get_data()
    mock_id = data["edit_mock_id"]
    raw = message.text.strip()
    if raw.lower().startswith("izoh:"):
        new_desc = raw.split(":", 1)[1].strip()
        await update_mock_exam_description(mock_id, new_desc)
        await state.clear()
        await message.answer("✅ Izoh yangilandi.", reply_markup=v2_mock_management_menu_kb())
        return
    try:
        datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "Format noto'g'ri. Masalan: 2026-09-20 10:00, yoki izoh uchun \"izoh: matn\" deb yozing."
        )
        return
    await update_mock_exam_date(mock_id, raw)
    await state.clear()
    await message.answer("✅ Sana yangilandi.", reply_markup=v2_mock_management_menu_kb())


@router.message(F.text == BTN_MY_GROUP, IsMentor())
async def btn_my_group(message: Message) -> None:
    from database.repo_cells import generate_invite_code

    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer("Sizga biriktirilgan faol guruh yo'q.")
        return
    lines = ["👥 <b>Mening guruhim</b>"]
    for cell in cells:
        partners = await list_cell_partners(cell["id"])
        lines.append(f"\n📚 {cell['direction_name']} ({len(partners)} ta partner):")
        for p in partners:
            uname = f" (@{p['username']})" if p["username"] else ""
            lines.append(f"  • {p['full_name']}{uname}")
    await message.answer("\n".join(lines))
    if len(cells) == 1:
        try:
            code = await generate_invite_code(cells[0]["id"])
            await message.answer(f"🔑 Yangi taklif kodi: <code>{code}</code> (24 soat amal qiladi)")
        except Exception as e:
            await message.answer(f"Kod generatsiya qilinmadi: {e}")


# ---------------------------------------------------------------------------
# 👑 Admin paneli (v2) — delegates most work to existing v1 admin handlers,
# adds the new direction-category picker and monthly Excel trigger wiring.
# ---------------------------------------------------------------------------

@router.message(F.text == BTN_ADMIN_PANEL)
async def btn_admin_panel(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("👑 Admin paneli:", reply_markup=admin_panel_v2_kb())


@router.message(F.text == BTN_CREATE_DIRECTION_V2)
async def btn_create_direction_v2(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        return
    await state.set_state(V2DirectionCreation.waiting_name)
    await message.answer("Yangi yo'nalish nomini kiriting (masalan: IELTS yoki SAT):")


@router.message(V2DirectionCreation.waiting_name, F.text)
async def process_v2_direction_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if await direction_name_exists(name):
        await message.answer("Bu nomdagi yo'nalish allaqachon mavjud.")
        return
    await state.update_data(name=name)
    await state.set_state(V2DirectionCreation.waiting_category)
    await message.answer("Yo'nalish toifasini tanlang:", reply_markup=direction_category_kb())


@router.callback_query(V2DirectionCreation.waiting_category, F.data.startswith("dircat:"))
async def process_v2_direction_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":")[1]
    data = await state.get_data()
    direction_id = await create_direction(data["name"])
    await set_direction_category(direction_id, category)

    category_label = "Mentorli yo'nalish" if category == "mentor_led" else "Tengdoshlar (Peer-to-peer)"
    await state.clear()
    await callback.message.answer(f"✅ Yo'nalish yaratildi: {data['name']} ({category_label})")
    await callback.answer()


@router.message(F.text == BTN_OPEN_CELL_ASSIGN)
async def btn_open_cell_assign(message: Message, state: FSMContext) -> None:
    """Opens the unified inline drill-down tree (Yo'nalishlar va Guruhlar):
    Yo'nalish -> Guruh -> A'zo -> Profil. Implemented in
    handlers/admin_manage.py; both this button and "⚙️ Hujayralar
    boshqaruvi" open the exact same panel so there is only one place to
    manage directions/cells/members."""
    if not await is_admin(message.from_user.id):
        return
    from handlers.admin_manage import cmd_admin_manage

    await cmd_admin_manage(message, state)


@router.message(F.text == BTN_CELL_MANAGEMENT)
async def btn_cell_management(message: Message, state: FSMContext) -> None:
    """Same panel as BTN_OPEN_CELL_ASSIGN (see docstring above) — kept as a
    separate button label for now since it's still wired into the reply
    keyboard, but both open the identical inline tree so there's no
    duplicate/confusing flow anymore."""
    if not await is_admin(message.from_user.id):
        return
    from handlers.admin_manage import cmd_admin_manage

    await cmd_admin_manage(message, state)


@router.message(F.text == BTN_MONTHLY_EXCEL)
async def btn_monthly_excel(message: Message) -> None:
    """Delegates to the existing v1 admin_manage.py 'Hisobot' flow, which
    already calls services/excel_export.py to build the monthly report."""
    if not await is_admin(message.from_user.id):
        return
    await message.answer("Oylik Excel hisobotini olish uchun \"📊 Hisobot\" bo'limidan foydalaning (Admin v1 paneli).")


# ---------------------------------------------------------------------------
# 🌐 Guruhlar va Reyting (public directory + leaderboard)
# ---------------------------------------------------------------------------

@router.message(F.text == BTN_GROUPS_RATING)
async def btn_groups_rating(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🌐 Guruhlar va Reyting:", reply_markup=groups_rating_kb())


@router.message(Command("guruhlar"))
@router.message(F.text == "🌐 Guruhlar ro'yxati")
async def cmd_directory(message: Message) -> None:
    await _send_directory(message)


async def _send_directory(message: Message) -> None:
    # NOTE: repo_cells.list_all_cells() uses an INNER JOIN on
    # users.telegram_id = cells.mentor_id, which silently drops
    # peer_to_peer cells (mentor_id IS NULL) from the results. Since
    # patch_and_update.py made mentor_id nullable, we use a LEFT JOIN
    # variant here (repo_v2.list_all_cells_including_peer_to_peer) so the
    # public directory shows every active cell, mentored or not, instead of
    # silently hiding peer-to-peer groups.
    from database.repo_v2 import list_all_cells_including_peer_to_peer

    cells = await list_all_cells_including_peer_to_peer()
    if not cells:
        await message.answer("Hozircha hech qanday faol guruh yo'q.")
        return
    lines = ["🌐 <b>Barcha yo'nalishlar va guruhlar</b>"]
    for cell in cells:
        mentor_label = cell["mentor_name"] if cell["mentor_name"] else "mentor yo'q (peer-to-peer)"
        lines.append(f"\n📚 <b>{cell['direction_name']}</b> — {mentor_label}")
        partners = await list_cell_partners(cell["id"])
        if partners:
            for p in partners:
                uname = f" (@{p['username']})" if p["username"] else ""
                lines.append(f"  • {p['full_name']}{uname}")
        else:
            lines.append("  (hozircha a'zo yo'q)")
        avg = await cell_average_points(cell["id"])
        lines.append(f"  📊 Guruh balli (o'rtacha): {avg:.1f}")
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_LEADERBOARD)
async def btn_leaderboard(message: Message) -> None:
    rows = await list_leaderboard(limit=20)
    if not rows:
        await message.answer("Hozircha ballar mavjud emas.")
        return
    lines = ["🏆 <b>Leaderboard</b>"]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, r in enumerate(rows, start=1):
        prefix = medals.get(i, f"{i}.")
        uname = f" (@{r['username']})" if r["username"] else ""
        lines.append(f"{prefix} {r['full_name']}{uname} — {r['total_points']} ball")
    await message.answer("\n".join(lines))


# ---------------------------------------------------------------------------
# Quota-error surface: any QuotaError raised elsewhere in v1 flows that
# route through repo_quotas (e.g. if mentor_partners.py or admin_mentor.py
# is later updated to call assert_can_join_as_partner /
# assert_can_become_mentor before inserting) is shown to the user cleanly
# instead of surfacing as an unhandled exception / raw IntegrityError.
# ---------------------------------------------------------------------------

@router.error(ExceptionTypeFilter(QuotaError))
async def on_quota_error(event: ErrorEvent) -> bool:
    e = event.exception
    update = event.update
    if update.message:
        await update.message.answer(f"❌ {e}")
    elif update.callback_query:
        await update.callback_query.answer(str(e), show_alert=True)
        if update.callback_query.message:
            await update.callback_query.message.answer(f"❌ {e}")
    return True


async def on_any_error(event: ErrorEvent, state: FSMContext | None = None) -> bool:
    """Safety net for any unhandled exception (e.g. a DB error). Without
    this, a callback button whose handler raises never gets answered, so
    Telegram shows it as stuck/unresponsive, and any FSM state involved
    stays set, causing unrelated later taps to be misrouted. This ensures
    the button always resolves and clears any stuck FSM state. Registered
    dispatcher-wide from bot.py so it covers every router, not just this
    one."""
    logger.exception("Unhandled error while processing update", exc_info=event.exception)
    if state is not None:
        try:
            await state.clear()
        except Exception:
            pass
    update = event.update
    if update.callback_query:
        try:
            await update.callback_query.answer(
                "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True
            )
        except Exception:
            pass
        if update.callback_query.message:
            try:
                await update.callback_query.message.answer(
                    "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring."
                )
            except Exception:
                pass
    elif update.message:
        try:
            await update.message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        except Exception:
            pass
    return True
