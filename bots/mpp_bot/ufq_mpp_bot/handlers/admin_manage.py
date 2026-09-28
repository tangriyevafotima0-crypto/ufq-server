from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repo_cells import (
    CellError,
    add_partner,
    create_cell,
    deactivate_cell,
    get_cell,
    get_cells_for_direction,
    list_cell_partners,
    move_partner_to_cell,
    remove_partner,
    rename_cell,
)
from database.repo_directions import (
    archive_direction,
    count_cells_in_direction,
    create_direction,
    direction_name_exists,
    get_direction,
    list_directions,
    rename_direction,
)
from database.repo_tasks import count_completed_submissions
from database.repo_users import get_user, get_user_roles_in_cells
from database.repo_v2 import (
    list_all_cells_including_peer_to_peer,
    list_upcoming_mock_exams_for_cell,
    sum_points_for_user,
)
from database.repo_zoom import list_upcoming_zoom_sessions_for_cell
from utils.timez import humanize
from handlers.states import (
    AdminOverride,
    CellRename,
    DirectionCreateTree,
    DirectionRename,
)
from keyboards.inline import (
    dir_tree_cancel_kb,
    dir_tree_cell_kb,
    dir_tree_confirm_kb,
    dir_tree_direction_kb,
    dir_tree_move_target_cells_kb,
    dir_tree_profile_kb,
    dir_tree_root_kb,
)
from keyboards.reply import cancel_kb, remove_kb
from middlewares.access import IsAdmin
from services.excel_export import build_monthly_report
from services.notifier import build_invite_link
from utils import texts

router = Router(name="admin_manage")
router.message.filter(IsAdmin())


# ---------------------------------------------------------------------------
# Root: Yo'nalishlar va Guruhlar
# ---------------------------------------------------------------------------

@router.message(Command("admin_boshqaruv"))
@router.message(F.text == "🛠 Boshqaruv")
@router.message(F.text == "👥 Guruh ochish va a'zolarni biriktirish")
async def cmd_admin_manage(message: Message, state: FSMContext) -> None:
    await state.clear()
    directions = await list_directions()
    await message.answer(
        "👥 <b>Yo'nalishlar va Guruhlar</b>\n\nBoshqarish uchun yo'nalishni tanlang:",
        reply_markup=dir_tree_root_kb(directions),
    )


@router.callback_query(F.data == "dt_root")
async def cb_dt_root(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    directions = await list_directions()
    try:
        await callback.message.edit_text(
            "👥 <b>Yo'nalishlar va Guruhlar</b>\n\nBoshqarish uchun yo'nalishni tanlang:",
            reply_markup=dir_tree_root_kb(directions),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()


@router.callback_query(F.data == "dt_new_dir")
async def cb_dt_new_dir(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DirectionCreateTree.waiting_name)
    await callback.message.answer(
        "Yangi yo'nalish nomini kiriting:", reply_markup=dir_tree_cancel_kb("dt_root")
    )
    await callback.answer()


@router.message(DirectionCreateTree.waiting_name, F.text)
async def process_dt_new_dir_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if await direction_name_exists(name):
        await message.answer(texts.DIRECTION_ALREADY_EXISTS)
        return
    await create_direction(name)
    await state.clear()
    await message.answer(f"✅ Yo'nalish yaratildi: {name}")
    directions = await list_directions()
    await message.answer("👥 <b>Yo'nalishlar va Guruhlar</b>", reply_markup=dir_tree_root_kb(directions))


# ---------------------------------------------------------------------------
# Yo'nalish ichi: Guruhlar ro'yxati
# ---------------------------------------------------------------------------

async def _render_direction(callback: CallbackQuery, direction_id: int) -> None:
    direction = await get_direction(direction_id)
    if direction is None:
        await callback.answer("Yo'nalish topilmadi.", show_alert=True)
        return
    cells = await get_cells_for_direction(direction_id, include_inactive=False)
    text = f"📚 <b>{direction['name']}</b>\n\nGuruhlar:"
    if not cells:
        text += "\n— hozircha guruh yo'q —"
    try:
        await callback.message.edit_text(text, reply_markup=dir_tree_direction_kb(direction_id, cells))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


@router.callback_query(F.data.startswith("dt_dir:"))
async def cb_dt_direction(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    direction_id = int(callback.data.split(":")[1])
    await _render_direction(callback, direction_id)
    await callback.answer()


@router.callback_query(F.data.startswith("dt_dir_rename:"))
async def cb_dt_dir_rename(callback: CallbackQuery, state: FSMContext) -> None:
    direction_id = int(callback.data.split(":")[1])
    await state.update_data(direction_id=direction_id)
    await state.set_state(DirectionRename.waiting_name)
    await callback.message.answer(
        "Yo'nalishning yangi nomini kiriting:",
        reply_markup=dir_tree_cancel_kb(f"dt_dir:{direction_id}"),
    )
    await callback.answer()


@router.message(DirectionRename.waiting_name, F.text)
async def process_dir_rename(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    direction_id = data["direction_id"]
    new_name = message.text.strip()
    if await direction_name_exists(new_name):
        await message.answer(texts.DIRECTION_ALREADY_EXISTS)
        return
    await rename_direction(direction_id, new_name)
    await state.clear()
    await message.answer(f"✅ Yo'nalish nomi o'zgartirildi: {new_name}")
    direction = await get_direction(direction_id)
    cells = await get_cells_for_direction(direction_id)
    await message.answer(
        f"📚 <b>{direction['name']}</b>\n\nGuruhlar:",
        reply_markup=dir_tree_direction_kb(direction_id, cells),
    )


@router.callback_query(F.data.startswith("dt_dir_archive:"))
async def cb_dt_dir_archive_confirm(callback: CallbackQuery) -> None:
    direction_id = int(callback.data.split(":")[1])
    count = await count_cells_in_direction(direction_id)
    await callback.message.answer(
        f"⚠️ Ushbu yo'nalishda {count} ta faol guruh bor. Rostdan ham arxivlaysizmi?\n"
        f"(Ballar va tarix saqlanib qoladi, faqat ko'rinishdan yashiriladi)",
        reply_markup=dir_tree_confirm_kb(f"dt_dir_archive_yes:{direction_id}", f"dt_dir:{direction_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dt_dir_archive_yes:"))
async def cb_dt_dir_archive_yes(callback: CallbackQuery) -> None:
    direction_id = int(callback.data.split(":")[1])
    await archive_direction(direction_id)
    await callback.message.answer("🗑 Yo'nalish arxivlandi.")
    directions = await list_directions()
    await callback.message.answer("👥 <b>Yo'nalishlar va Guruhlar</b>", reply_markup=dir_tree_root_kb(directions))
    await callback.answer()


@router.callback_query(F.data.startswith("dt_new_cell:"))
async def cb_dt_new_cell(callback: CallbackQuery) -> None:
    direction_id = int(callback.data.split(":")[1])
    await create_cell(direction_id, mentor_id=None)
    await callback.answer("Guruh yaratildi ✅")
    await _render_direction(callback, direction_id)


# ---------------------------------------------------------------------------
# Guruh ichi
# ---------------------------------------------------------------------------

async def _render_cell(callback: CallbackQuery, cell_id: int) -> None:
    cell = await get_cell(cell_id)
    if cell is None:
        await callback.answer("Guruh topilmadi.", show_alert=True)
        return
    partners = await list_cell_partners(cell_id)
    direction = await get_direction(cell["direction_id"])
    header = f"📚 <b>{direction['name']}</b> — Guruh #{cell_id}"

    mocks = await list_upcoming_mock_exams_for_cell(cell_id)
    if mocks:
        mock_lines = "\n".join(f"  • {humanize(m['exam_date'])}" for m in mocks)
        mock_block = f"\n\n🎯 <b>Mock sanalari:</b>\n{mock_lines}"
    else:
        mock_block = "\n\n🎯 <b>Mock sanalari:</b> belgilanmagan"

    zooms = await list_upcoming_zoom_sessions_for_cell(cell_id)
    if zooms:
        zoom_lines = "\n".join(f"  • {humanize(z['session_at'])}" for z in zooms)
        zoom_block = f"\n\n🎥 <b>Zoom sanalari:</b>\n{zoom_lines}"
    else:
        zoom_block = "\n\n🎥 <b>Zoom sanalari:</b> belgilanmagan"

    text = f"{header}{mock_block}{zoom_block}\n\nA'zolar va boshqaruv:"
    try:
        await callback.message.edit_text(
            text,
            reply_markup=dir_tree_cell_kb(cell_id, cell["direction_id"], cell["mentor_id"], partners),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


@router.callback_query(F.data.startswith("dt_cell:"))
async def cb_dt_cell(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    cell_id = int(callback.data.split(":")[1])
    await _render_cell(callback, cell_id)
    await callback.answer()


@router.callback_query(F.data.startswith("dt_cell_rename:"))
async def cb_dt_cell_rename(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await state.set_state(CellRename.waiting_name)
    await callback.message.answer(
        "Guruhning yangi nomini kiriting:",
        reply_markup=dir_tree_cancel_kb(f"dt_cell:{cell_id}"),
    )
    await callback.answer()


@router.message(CellRename.waiting_name, F.text)
async def process_cell_rename(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data["cell_id"]
    new_label = message.text.strip()
    await rename_cell(cell_id, new_label)
    await state.clear()
    await message.answer(f"✅ Guruh nomi o'zgartirildi: {new_label}")


@router.callback_query(F.data.startswith("dt_cell_archive:"))
async def cb_dt_cell_archive_confirm(callback: CallbackQuery) -> None:
    cell_id = int(callback.data.split(":")[1])
    partners = await list_cell_partners(cell_id)
    await callback.message.answer(
        f"⚠️ Ushbu guruhda {len(partners)} nafar a'zo bor. Rostdan ham arxivlaysizmi?\n"
        f"(Ballar va tarix saqlanib qoladi, faqat ko'rinishdan yashiriladi)",
        reply_markup=dir_tree_confirm_kb(f"dt_cell_archive_yes:{cell_id}", f"dt_cell:{cell_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dt_cell_archive_yes:"))
async def cb_dt_cell_archive_yes(callback: CallbackQuery) -> None:
    cell_id = int(callback.data.split(":")[1])
    cell = await get_cell(cell_id)
    await deactivate_cell(cell_id)
    await callback.message.answer("🗑 Guruh arxivlandi.")
    if cell:
        await _render_direction(callback, cell["direction_id"])
    await callback.answer()


@router.callback_query(F.data.startswith("dt_invite:"))
async def cb_dt_invite(callback: CallbackQuery) -> None:
    cell_id = int(callback.data.split(":")[1])
    link = await build_invite_link(cell_id)
    await callback.message.answer(
        f"🔗 Taklif havolasi (doimiy, muddatsiz):\n{link}\n\n"
        f"Ushbu havolani bosgan foydalanuvchi avtomatik ushbu guruhga qo'shiladi "
        f"(joy va kvota mavjud bo'lsa)."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dt_add_partner:"))
async def cb_dt_add_partner(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id)
    await state.set_state(AdminOverride.waiting_user_for_add)
    await callback.message.answer(
        texts.ASK_PARTNER_USERNAME,
        reply_markup=dir_tree_cancel_kb(f"dt_cell:{cell_id}"),
    )
    await callback.answer()


@router.message(AdminOverride.waiting_user_for_add, F.text)
async def process_admin_add_partner(message: Message, state: FSMContext) -> None:
    from utils.validators import is_telegram_id, normalize_username
    from database.repo_users import get_user_by_username

    data = await state.get_data()
    cell_id = data["cell_id"]
    is_mentor_change = data.get("mentor_change", False)
    raw = message.text.strip()
    if is_telegram_id(raw):
        user = await get_user(int(raw))
    else:
        user = await get_user_by_username(normalize_username(raw))
    if user is None:
        await message.answer(texts.USER_NOT_FOUND)
        return

    if is_mentor_change:
        from database.repo_cells import set_cell_mentor

        try:
            await set_cell_mentor(cell_id, user["telegram_id"])
        except CellError as e:
            await message.answer(str(e), reply_markup=remove_kb())
            await state.clear()
            return
        await state.clear()
        await message.answer(f"✅ {user['full_name']} endi ushbu guruhda mentor.", reply_markup=remove_kb())
        return

    try:
        await add_partner(cell_id, user["telegram_id"])
    except CellError as e:
        await message.answer(str(e), reply_markup=remove_kb())
        await state.clear()
        return
    await state.clear()
    await message.answer(
        texts.PARTNER_ADDED.format(partner_name=user["full_name"]),
        reply_markup=remove_kb(),
    )


@router.callback_query(F.data.startswith("dt_mentor_change:"))
async def cb_dt_mentor_change(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    await state.update_data(cell_id=cell_id, mentor_change=True)
    await state.set_state(AdminOverride.waiting_user_for_add)
    await callback.message.answer(
        "Yangi mentorning @username yoki Telegram ID raqamini yuboring:",
        reply_markup=dir_tree_cancel_kb(f"dt_cell:{cell_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dt_mentor_release:"))
async def cb_dt_mentor_release(callback: CallbackQuery) -> None:
    from database.repo_cells import release_cell_mentor

    cell_id = int(callback.data.split(":")[1])
    await release_cell_mentor(cell_id)
    await callback.message.answer("🚫 Mentor guruhdan bo'shatildi.")
    await _render_cell(callback, cell_id)
    await callback.answer()


# ---------------------------------------------------------------------------
# A'zo profil kartochkasi
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("dt_profile:"))
async def cb_dt_profile(callback: CallbackQuery) -> None:
    _, cell_id_str, target_id_str, role = callback.data.split(":")
    cell_id, target_id = int(cell_id_str), int(target_id_str)
    user = await get_user(target_id)
    if user is None:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return
    cell = await get_cell(cell_id)
    roles = await get_user_roles_in_cells(target_id)
    role_lines = []
    for r in roles:
        tag = "Mentor" if r["role"] == "mentor" else "Partner"
        role_lines.append(f"  • {r['direction_name']} [{tag}]")
    total_points = await sum_points_for_user(target_id)
    completed = await count_completed_submissions(target_id)

    uname = f"@{user['username']}" if user["username"] else "—"
    text = (
        f"👤 <b>{user['full_name']}</b>\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: {uname}\n"
        f"Roli: {'Mentor' if role == 'mentor' else 'Partner'}\n\n"
        f"Ishtirokidagi yo'nalishlar:\n" + ("\n".join(role_lines) if role_lines else "  — yo'q —") + "\n\n"
        f"📊 <b>Statistika</b>\n"
        f"🏆 Jami ball: {total_points}\n"
        f"✅ Bajarilgan vazifalar: {completed}"
    )
    await callback.message.answer(
        text, reply_markup=dir_tree_profile_kb(cell_id, target_id, role, cell["direction_id"] if cell else 0)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dt_kick:"))
async def cb_dt_kick(callback: CallbackQuery) -> None:
    _, cell_id_str, partner_id_str = callback.data.split(":")
    cell_id, partner_id = int(cell_id_str), int(partner_id_str)
    user = await get_user(partner_id)
    await remove_partner(cell_id, partner_id)
    await callback.message.answer(
        texts.PARTNER_REMOVED.format(partner_name=user["full_name"] if user else partner_id)
    )
    await _render_cell(callback, cell_id)
    await callback.answer()


@router.callback_query(F.data.startswith("dt_move:"))
async def cb_dt_move_pick_target(callback: CallbackQuery, state: FSMContext) -> None:
    _, cell_id_str, partner_id_str = callback.data.split(":")
    cell_id, partner_id = int(cell_id_str), int(partner_id_str)
    cell = await get_cell(cell_id)
    all_cells = await list_all_cells_including_peer_to_peer()
    same_direction = [c for c in all_cells if c["direction_id"] == cell["direction_id"]]
    if len(same_direction) <= 1:
        await callback.answer("Bu yo'nalishda boshqa faol guruh yo'q.", show_alert=True)
        return
    await state.update_data(from_cell_id=cell_id, partner_id=partner_id)
    await callback.message.answer(
        "Qaysi guruhga ko'chirmoqchisiz?",
        reply_markup=dir_tree_move_target_cells_kb(same_direction, cell_id, "dt_move_to"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dt_move_to:"))
async def cb_dt_move_to(callback: CallbackQuery, state: FSMContext) -> None:
    to_cell_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    from_cell_id = data.get("from_cell_id")
    partner_id = data.get("partner_id")
    if from_cell_id is None or partner_id is None:
        await callback.answer("Sessiya eskirgan, qaytadan urinib ko'ring.", show_alert=True)
        return
    try:
        await move_partner_to_cell(from_cell_id, to_cell_id, partner_id)
    except CellError as e:
        await callback.message.answer(f"❌ {e}")
        await state.clear()
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer("✅ A'zo boshqa guruhga ko'chirildi.")
    await callback.answer()


# ---------------------------------------------------------------------------
# Monthly Excel report (unchanged from v1)
# ---------------------------------------------------------------------------

@router.message(Command("hisobot"))
@router.message(F.text == "📊 Hisobot")
async def cmd_report(message: Message) -> None:
    await message.answer(texts.REPORT_GENERATING)
    from aiogram.types import FSInputFile

    path = await build_monthly_report()
    await message.answer_document(FSInputFile(path), caption="📊 So'nggi hisobot")
