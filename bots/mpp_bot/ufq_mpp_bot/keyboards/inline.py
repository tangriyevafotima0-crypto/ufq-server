from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def directions_kb(directions, prefix: str, show_status: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in directions:
        label = d["name"]
        if show_status:
            label += " ✅" if d["is_active"] else " ⛔️"
        builder.button(text=label, callback_data=f"{prefix}:{d['id']}")
    builder.adjust(1)
    return builder.as_markup()


def cells_kb(cells, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in cells:
        direction_name = c["direction_name"] if "direction_name" in c.keys() else ""
        mentor_name = c["mentor_name"] if "mentor_name" in c.keys() else ""
        label = f"{direction_name}"
        if mentor_name:
            label += f" — {mentor_name}"
        builder.button(text=label, callback_data=f"{prefix}:{c['id']}")
    builder.adjust(1)
    return builder.as_markup()


def users_kb(users, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users:
        label = u["full_name"]
        if u["username"]:
            label += f" (@{u['username']})"
        builder.button(text=label, callback_data=f"{prefix}:{u['telegram_id']}")
    builder.adjust(1)
    return builder.as_markup()


def partners_kb(partners, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in partners:
        label = p["full_name"]
        if p["username"]:
            label += f" (@{p['username']})"
        builder.button(text=label, callback_data=f"{prefix}:{p['telegram_id']}")
    builder.adjust(1)
    return builder.as_markup()


def tasks_kb(tasks, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(text=t["title"], callback_data=f"{prefix}:{t['id']}")
    builder.adjust(1)
    return builder.as_markup()


def partner_method_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Username / ID kiritish", callback_data="partner_method:manual")
    builder.button(text="🔑 Taklif kodi generatsiya qilish", callback_data="partner_method:code")
    builder.adjust(1)
    return builder.as_markup()


def task_status_kb(submission_id: int, current_status: str | None = None) -> InlineKeyboardMarkup | None:
    if current_status == "bajardi":
        return None
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Bajardim", callback_data=f"status:{submission_id}:bajardi")
    builder.button(text="🔄 Jarayonda", callback_data=f"status:{submission_id}:jarayonda")
    builder.button(text="❌ Bajarmadim", callback_data=f"status:{submission_id}:bajarmadi")
    builder.adjust(1)
    return builder.as_markup()


def partner_kick_kb(partners, cell_id: int, prefix: str = "kick") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in partners:
        label = f"❌ {p['full_name']}"
        builder.button(text=label, callback_data=f"{prefix}:{cell_id}:{p['telegram_id']}")
    builder.adjust(1)
    return builder.as_markup()


def mentor_partners_list_kb(partners, cell_id: int) -> InlineKeyboardMarkup:
    """Mentor's 'Partnerlarim' list: tapping a partner opens their profile
    card (mentor_profile_kb) instead of instantly removing them."""
    builder = InlineKeyboardBuilder()
    for p in partners:
        builder.button(text=f"👤 {p['full_name']}", callback_data=f"mp_profile:{cell_id}:{p['telegram_id']}")
    builder.adjust(1)
    return builder.as_markup()


def mentor_partner_profile_kb(cell_id: int, partner_id: int) -> InlineKeyboardMarkup:
    """Boshqaruv tugmalari on a mentor-viewed partner profile: remove from
    the group, or move to another of the mentor's own groups."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Guruhdan chiqarish", callback_data=f"mp_kick:{cell_id}:{partner_id}")
    builder.button(text="🔄 Boshqa guruhga o'tkazish", callback_data=f"mp_move:{cell_id}:{partner_id}")
    builder.button(text="🔙 Orqaga", callback_data=f"mp_back:{cell_id}")
    builder.adjust(1)
    return builder.as_markup()


def mentor_move_target_cells_kb(cells, exclude_cell_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in cells:
        if c["id"] == exclude_cell_id:
            continue
        label = c["direction_name"] if "direction_name" in c.keys() else f"Guruh #{c['id']}"
        builder.button(text=label, callback_data=f"mp_move_to:{c['id']}")
    builder.adjust(1)
    return builder.as_markup()


def admin_manage_kb(cells) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in cells:
        direction_name = c["direction_name"]
        mentor_name = c["mentor_name"]
        builder.button(text=f"{direction_name} — {mentor_name}", callback_data=f"admin_cell:{c['id']}")
    builder.adjust(1)
    return builder.as_markup()


def admin_cell_actions_kb(cell_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Partner qo'shish", callback_data=f"admin_add_partner:{cell_id}")
    builder.button(text="➖ Partnerni chiqarish", callback_data=f"admin_remove_partner:{cell_id}")
    builder.button(text="🗑 Hujayrani bekor qilish", callback_data=f"admin_deactivate_cell:{cell_id}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=yes_cb)
    builder.button(text="❌ Yo'q", callback_data=no_cb)
    builder.adjust(2)
    return builder.as_markup()


def view_my_tasks_kb() -> InlineKeyboardMarkup:
    """Single unambiguous action for multi-task reminders: opens the full
    /holat view (each task with its own status buttons) instead of guessing
    which of several tasks a lone inline button would apply to.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Vazifalarimni ko'rish", callback_data="open_my_status")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Drill-down tree: Yo'nalishlar va Guruhlar
# (Yo'nalish -> Guruh -> A'zo -> Profil)
# ---------------------------------------------------------------------------

def dir_tree_root_kb(directions) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in directions:
        status = "✅" if d["is_active"] else "⛔️"
        builder.button(text=f"{status} {d['name']}", callback_data=f"dt_dir:{d['id']}")
    builder.button(text="➕ Yangi yo'nalish qo'shish", callback_data="dt_new_dir")
    builder.adjust(1)
    return builder.as_markup()


def dir_tree_direction_kb(direction_id: int, cells) -> InlineKeyboardMarkup:
    from database.repo_cells import cell_display_label

    builder = InlineKeyboardBuilder()
    for c in cells:
        status = "✅" if c["is_active"] else "⛔️"
        builder.button(text=f"{status} {cell_display_label(c)}", callback_data=f"dt_cell:{c['id']}")
    builder.button(text="➕ Yangi guruh yaratish", callback_data=f"dt_new_cell:{direction_id}")
    builder.button(text="✏️ Nomini o'zgartirish", callback_data=f"dt_dir_rename:{direction_id}")
    builder.button(text="🗑 Yo'nalishni arxivlash", callback_data=f"dt_dir_archive:{direction_id}")
    builder.button(text="🔙 Orqaga", callback_data="dt_root")
    builder.adjust(1)
    return builder.as_markup()


def dir_tree_cell_kb(cell_id: int, direction_id: int, mentor_id: int | None, partners) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Taklif havolasi", callback_data=f"dt_invite:{cell_id}")
    if mentor_id:
        builder.button(text="🧑‍🏫 Mentor profili", callback_data=f"dt_profile:{cell_id}:{mentor_id}:mentor")
        builder.button(text="🔄 Mentorni o'zgartirish", callback_data=f"dt_mentor_change:{cell_id}")
        builder.button(text="🚫 Mentorni bo'shatish", callback_data=f"dt_mentor_release:{cell_id}")
    else:
        builder.button(text="🧑‍🏫 Mentor tayinlash", callback_data=f"dt_mentor_change:{cell_id}")
    for p in partners:
        label = f"👤 {p['full_name']}"
        builder.button(text=label, callback_data=f"dt_profile:{cell_id}:{p['telegram_id']}:partner")
    builder.button(text="➕ Partner qo'shish", callback_data=f"dt_add_partner:{cell_id}")
    builder.button(text="✏️ Tahrirlash (nomi)", callback_data=f"dt_cell_rename:{cell_id}")
    builder.button(text="🗑 Guruhni arxivlash", callback_data=f"dt_cell_archive:{cell_id}")
    builder.button(text="🔙 Orqaga", callback_data=f"dt_dir:{direction_id}")
    builder.adjust(1)
    return builder.as_markup()


def dir_tree_profile_kb(cell_id: int, target_id: int, role: str, direction_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if role == "partner":
        builder.button(text="❌ Guruhdan chiqarish", callback_data=f"dt_kick:{cell_id}:{target_id}")
        builder.button(text="🔄 Boshqa guruhga ko'chirish", callback_data=f"dt_move:{cell_id}:{target_id}")
    else:
        builder.button(text="🚫 Mentorlikdan bo'shatish", callback_data=f"dt_mentor_release:{cell_id}")
    builder.button(text="🔙 Orqaga", callback_data=f"dt_cell:{cell_id}")
    builder.adjust(1)
    return builder.as_markup()


def dir_tree_confirm_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=yes_cb)
    builder.button(text="❌ Bekor qilish", callback_data=no_cb)
    builder.adjust(2)
    return builder.as_markup()


def dir_tree_cancel_kb(back_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data=back_cb)
    return builder.as_markup()


def dir_tree_move_target_cells_kb(cells, exclude_cell_id: int, prefix: str) -> InlineKeyboardMarkup:
    from database.repo_cells import cell_display_label

    builder = InlineKeyboardBuilder()
    for c in cells:
        if c["id"] == exclude_cell_id:
            continue
        builder.button(text=cell_display_label(c), callback_data=f"{prefix}:{c['id']}")
    builder.adjust(1)
    return builder.as_markup()
