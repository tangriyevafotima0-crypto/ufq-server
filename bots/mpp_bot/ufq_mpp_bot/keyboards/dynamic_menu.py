"""
keyboards/dynamic_menu.py
--------------------------
Role-driven persistent reply keyboard (main menu) plus the inline sub-panel
keyboards for the v2 features: O'qish paneli (partner), Mentor paneli,
Admin paneli, and Guruhlar va Reyting.

This module is purely additive: it does not replace keyboards/reply.py's
existing admin_menu_kb / mentor_menu_kb / partner_menu_kb, which the v1
handlers (admin_directions, admin_mentor, admin_manage, mentor_partners,
mentor_tasks, mentor_mock, partner_status) still render on their own. The
v2 main menu below is a separate, additional entry point (see handlers/
v2_panels.py) that fans out into these v1 panels via their existing text
triggers where possible, plus the brand-new v2 screens.
"""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

# ---------------------------------------------------------------------------
# Persistent reply keyboard button labels (must match handlers/v2_panels.py
# F.text filters exactly).
# ---------------------------------------------------------------------------

BTN_GROUPS_RATING = "🌐 Guruhlar va Reyting"
BTN_STUDY_PANEL = "📚 O'qish paneli"
BTN_MENTOR_PANEL = "🎓 Mentor paneli"
BTN_ADMIN_PANEL = "👑 Admin paneli"
BTN_MAIN_MENU = "⬅️ Asosiy menyu"

# O'qish paneli (partner) sub-buttons
BTN_MY_PARTNERS_MENTOR = "👥 Sheriklarim va Mentorim"
BTN_MY_TASKS = "📋 Vazifalarim"
BTN_CELL_MOCK_DATES = "🎯 Guruh Mock sanalari"
BTN_MY_RESULTS = "📊 Shaxsiy natijam"
BTN_JOIN_BY_CODE = "🔑 Kod bilan qo'shilish"

# Mentor paneli sub-buttons
BTN_UPLOAD_WEEKLY_PLAN = "📅 7 kunlik reja yuklash"
BTN_ZOOM_STATUS = "📹 Zoom dars holati"
BTN_MOCK_MANAGEMENT = "🎯 Mock boshqaruvi"
BTN_MOCK_DATE_SCHEDULE = "📅 Mock sanasini belgilash"
BTN_MY_GROUP = "👥 Mening guruhim"
BTN_WEEKLY_PLAN_MANAGE = "🗓 Haftalik reja boshqaruvi"
BTN_ZOOM_SCHEDULE_MANAGE = "🎥 Zoom sanalari"

# Study paneli (partner) additional sub-buttons
BTN_MY_WEEKLY_PLAN = "🗓 Haftalik rejam"
BTN_CELL_ZOOM_DATES = "🎥 Guruh Zoom sanalari"

# Admin paneli sub-buttons
BTN_CREATE_DIRECTION_V2 = "📚 Yo'nalish yaratish"
BTN_OPEN_CELL_ASSIGN = "👥 Guruh ochish va a'zolarni biriktirish"
BTN_CELL_MANAGEMENT = "⚙️ Hujayralar boshqaruvi"
BTN_MONTHLY_EXCEL = "📈 Oylik Session Excel hisoboti"

# Guruhlar va Reyting sub-buttons
BTN_LEADERBOARD = "🏆 Leaderboard"


# ---------------------------------------------------------------------------
# Persistent (reply) keyboards
# ---------------------------------------------------------------------------

def main_menu_kb(*, is_admin: bool, is_mentor: bool, is_partner: bool) -> ReplyKeyboardMarkup:
    """The dynamic main menu described in the spec: rows are added only for
    roles the user actually holds. [Guruhlar va Reyting] is always shown.
    """
    rows: list[list[KeyboardButton]] = [[KeyboardButton(text=BTN_GROUPS_RATING)]]

    second_row: list[KeyboardButton] = []
    if is_partner:
        second_row.append(KeyboardButton(text=BTN_STUDY_PANEL))
    if is_mentor:
        second_row.append(KeyboardButton(text=BTN_MENTOR_PANEL))
    if second_row:
        rows.append(second_row)

    if is_admin:
        rows.append([KeyboardButton(text=BTN_ADMIN_PANEL)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def study_panel_kb(*, show_join_by_code: bool) -> ReplyKeyboardMarkup:
    """O'qish paneli (Partner paneli). The '🔑 Kod bilan qo'shilish' button is
    conditional: only shown while the user is an active partner in fewer
    than MAX_CELLS_AS_PARTNER (2) cells (see database/repo_quotas.py) -- once
    they hit the quota it disappears rather than being shown and then
    rejected on tap.
    """
    rows = [
        [KeyboardButton(text=BTN_MY_PARTNERS_MENTOR)],
        [KeyboardButton(text=BTN_MY_TASKS)],
        [KeyboardButton(text=BTN_CELL_MOCK_DATES)],
        [KeyboardButton(text=BTN_MY_WEEKLY_PLAN)],
        [KeyboardButton(text=BTN_CELL_ZOOM_DATES)],
        [KeyboardButton(text=BTN_MY_RESULTS)],
    ]
    if show_join_by_code:
        rows.append([KeyboardButton(text=BTN_JOIN_BY_CODE)])
    rows.append([KeyboardButton(text=BTN_MAIN_MENU)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def mentor_panel_kb() -> ReplyKeyboardMarkup:
    """Mentor paneli."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_UPLOAD_WEEKLY_PLAN)],
            [KeyboardButton(text=BTN_WEEKLY_PLAN_MANAGE)],
            [KeyboardButton(text=BTN_ZOOM_STATUS)],
            [KeyboardButton(text=BTN_ZOOM_SCHEDULE_MANAGE)],
            [KeyboardButton(text=BTN_MOCK_MANAGEMENT)],
            [KeyboardButton(text=BTN_MOCK_DATE_SCHEDULE)],
            [KeyboardButton(text=BTN_MY_GROUP)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def admin_panel_v2_kb() -> ReplyKeyboardMarkup:
    """Admin paneli (v2). Kept separate from keyboards/reply.py's
    admin_menu_kb() (v1), which handlers/admin_directions.py,
    admin_mentor.py and admin_manage.py already listen for -- this new
    keyboard's buttons route into handlers/v2_panels.py, which re-uses
    those existing v1 flows under the hood where the feature already
    exists (direction creation, cell/partner management, Excel report).
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CREATE_DIRECTION_V2)],
            [KeyboardButton(text=BTN_OPEN_CELL_ASSIGN)],
            [KeyboardButton(text=BTN_CELL_MANAGEMENT)],
            [KeyboardButton(text=BTN_MONTHLY_EXCEL)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def groups_rating_kb() -> ReplyKeyboardMarkup:
    """Guruhlar va Reyting (visible to everyone)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LEADERBOARD)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ---------------------------------------------------------------------------
# Inline keyboards for v2 features
# ---------------------------------------------------------------------------

def direction_category_kb() -> InlineKeyboardMarkup:
    """Admin: choose direction category when creating a new yo'nalish."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🧑‍🏫 Mentorli yo'nalish", callback_data="dircat:mentor_led")
    builder.button(text="🤝 Tengdoshlar (Peer-to-peer)", callback_data="dircat:peer_to_peer")
    builder.adjust(1)
    return builder.as_markup()


def task_checkin_kb(progress_key: str) -> InlineKeyboardMarkup:
    """3-day check-in buttons for tasks_progress rows.

    progress_key encodes 'cell_id:cycle_date' (cycle_date = YYYY-MM-DD) so a
    single card covers the whole 3-day cycle for that cell, matching the
    'umumiy tekshiruv kartasi' (single combined check-in card) described in
    the spec's scheduler section, rather than one row per task.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Bajardim", callback_data=f"v2chk:{progress_key}:done")
    builder.button(text="⏳ Jarayonda", callback_data=f"v2chk:{progress_key}:progress")
    builder.button(text="❌ Bajarmadim", callback_data=f"v2chk:{progress_key}:failed")
    builder.adjust(1)
    return builder.as_markup()


def v2_cells_kb(cells, prefix: str) -> InlineKeyboardMarkup:
    """Same shape as keyboards/inline.py's cells_kb, duplicated locally so
    this module has no import-time dependency on keyboards/inline.py beyond
    what's already used elsewhere; safe to swap for the shared one later."""
    builder = InlineKeyboardBuilder()
    for c in cells:
        direction_name = c["direction_name"] if "direction_name" in c.keys() else ""
        label = direction_name or f"Guruh #{c['id']}"
        builder.button(text=label, callback_data=f"{prefix}:{c['id']}")
    builder.adjust(1)
    return builder.as_markup()


def v2_mock_exams_kb(mocks, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in mocks:
        label = f"{m['exam_date']} — {m['description'] or 'Mock'}"
        builder.button(text=label, callback_data=f"{prefix}:{m['id']}")
    builder.adjust(1)
    return builder.as_markup()


def v2_mock_management_menu_kb() -> InlineKeyboardMarkup:
    """Top-level 'Mock sanasini belgilash' entry: list, add, and browse
    archive, as requested — mentor picks an action first."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Mock sanalari (faol)", callback_data="v2mockdate_list")
    builder.button(text="➕ Yangi mock qo'shish", callback_data="v2mockdate_new")
    builder.button(text="🗄 Arxiv", callback_data="v2mockdate_archive_list")
    builder.adjust(1)
    return builder.as_markup()


def v2_mock_dates_list_kb(mocks, archived: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in mocks:
        label = m["auto_label"] if "auto_label" in dict(m) else (m["description"] or m["exam_date"])
        builder.button(text=f"📅 {label}", callback_data=f"v2mockdate_open:{m['id']}")
    builder.button(text="🔙 Orqaga", callback_data="v2mockdate_menu")
    builder.adjust(1)
    return builder.as_markup()


def v2_mock_date_detail_kb(mock_id: int, is_archived: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Tahrirlash", callback_data=f"v2mockdate_edit:{mock_id}")
    if is_archived:
        builder.button(text="♻️ Arxivdan chiqarish", callback_data=f"v2mockdate_unarchive:{mock_id}")
    else:
        builder.button(text="🗄 Arxivlash", callback_data=f"v2mockdate_archive:{mock_id}")
    builder.button(text="🗑 O'chirish", callback_data=f"v2mockdate_delete_confirm:{mock_id}")
    builder.button(text="➕ Yana bitta qo'shish", callback_data="v2mockdate_new")
    builder.button(text="🔙 Orqaga", callback_data="v2mockdate_menu")
    builder.adjust(1)
    return builder.as_markup()


def v2_mock_date_delete_confirm_kb(mock_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"v2mockdate_delete_yes:{mock_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"v2mockdate_open:{mock_id}")
    builder.adjust(2)
    return builder.as_markup()


def v2_partners_kb(partners, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in partners:
        label = p["full_name"]
        if p["username"]:
            label += f" (@{p['username']})"
        builder.button(text=label, callback_data=f"{prefix}:{p['telegram_id']}")
    builder.adjust(1)
    return builder.as_markup()


def weekly_plan_day_checkin_kb(plan_day_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Bajardim", callback_data=f"v2plan_day_chk:{plan_day_id}:bajardim")
    builder.button(text="❌ Bajarmadim", callback_data=f"v2plan_day_chk:{plan_day_id}:bajarmadim")
    builder.adjust(1)
    return builder.as_markup()


def weekly_plan_manage_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👁 Joriy rejani ko'rish", callback_data="v2plan_view")
    builder.button(text="✏️ Rejani tahrirlash", callback_data="v2plan_edit")
    builder.button(text="🗑 Rejani o'chirish", callback_data="v2plan_delete_confirm")
    builder.button(text="➕ Yangi hafta rejasi", callback_data="v2plan_new")
    builder.button(text="📥 Tasdiqlanmagan bajarilganlar", callback_data="v2plan_unconfirmed")
    builder.adjust(1)
    return builder.as_markup()


def weekly_plan_delete_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data="v2plan_delete_yes")
    builder.button(text="❌ Bekor qilish", callback_data="v2plan_menu_back")
    builder.adjust(2)
    return builder.as_markup()


def plan_day_edit_pick_kb(days) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in days:
        builder.button(text=f"{d['day_number']}-kun", callback_data=f"v2plan_edit_day:{d['id']}")
    builder.adjust(4)
    return builder.as_markup()


def plan_unconfirmed_kb(rows) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in rows:
        label = f"{r['day_number']}-kun: {r['full_name']}"
        builder.button(text=label, callback_data=f"v2plan_confirm:{r['id']}")
    builder.adjust(1)
    return builder.as_markup()


def zoom_manage_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Rejalashtirilganlar", callback_data="v2zoomdate_list")
    builder.button(text="➕ Yangi Zoom belgilash", callback_data="v2zoomdate_new")
    builder.button(text="💬 Partner takliflari", callback_data="v2zoomdate_suggestions")
    builder.adjust(1)
    return builder.as_markup()


def zoom_sessions_list_kb(sessions) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in sessions:
        builder.button(text=f"🎥 {s['session_at']}", callback_data=f"v2zoomdate_open:{s['id']}")
    builder.button(text="🔙 Orqaga", callback_data="v2zoomdate_menu")
    builder.adjust(1)
    return builder.as_markup()


def zoom_session_detail_kb(session_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Tahrirlash", callback_data=f"v2zoomdate_edit:{session_id}")
    builder.button(text="🗑 O'chirish", callback_data=f"v2zoomdate_delete_confirm:{session_id}")
    builder.button(text="➕ Yana bitta qo'shish", callback_data="v2zoomdate_new")
    builder.button(text="🔙 Orqaga", callback_data="v2zoomdate_menu")
    builder.adjust(1)
    return builder.as_markup()


def zoom_delete_confirm_kb(session_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"v2zoomdate_delete_yes:{session_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"v2zoomdate_open:{session_id}")
    builder.adjust(2)
    return builder.as_markup()


def zoom_post_check_kb(session_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'tdi", callback_data=f"v2zoompost:{session_id}:yes")
    builder.button(text="❌ Yo'q, o'tmadi", callback_data=f"v2zoompost:{session_id}:no")
    builder.adjust(1)
    return builder.as_markup()


def mock_score_significant_gain_kb(mock_id: int, user_id: int) -> InlineKeyboardMarkup:
    """After entering a raw score, mentor is asked whether it represents a
    significant improvement (spec: +1 bonus ball on top of the +2 for
    participating)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Ha, sezilarli o'sish bor", callback_data=f"mockgain:{mock_id}:{user_id}:yes")
    builder.button(text="➖ Yo'q, oddiy natija", callback_data=f"mockgain:{mock_id}:{user_id}:no")
    builder.adjust(1)
    return builder.as_markup()
