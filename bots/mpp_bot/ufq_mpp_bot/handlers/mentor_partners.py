from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repo_cells import (
    CellError,
    add_partner,
    assert_mentor_owns_cell,
    consume_invite_code,
    find_cell_by_invite_code,
    generate_invite_code,
    list_cell_partners,
    list_cells_for_mentor,
)
from database.repo_directions import get_direction
from database.repo_users import get_user, get_user_by_username
from handlers.states import JoinByCode, PartnerOnboarding
from keyboards.inline import (
    cells_kb,
    mentor_move_target_cells_kb,
    mentor_partner_profile_kb,
    mentor_partners_list_kb,
    partner_kick_kb,
    partner_method_kb,
)
from keyboards.reply import cancel_kb, remove_kb
from middlewares.access import IsMentor
from utils import texts
from utils.validators import is_telegram_id, is_valid_invite_code, normalize_username

router = Router(name="mentor_partners")


@router.message(Command("partner_qosh"), IsMentor())
@router.message(F.text == "➕ Partner qo'shish", IsMentor())
async def cmd_add_partner(message: Message, state: FSMContext) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer(texts.NO_ACTIVE_CELLS_MENTOR)
        return
    await state.set_state(PartnerOnboarding.waiting_cell)
    await message.answer(texts.ASK_CELL_FOR_PARTNER, reply_markup=cells_kb(cells, "padd_cell"))


@router.callback_query(PartnerOnboarding.waiting_cell, F.data.startswith("padd_cell:"))
async def process_cell_choice(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    try:
        await assert_mentor_owns_cell(callback.from_user.id, cell_id)
    except CellError as e:
        await callback.answer(str(e), show_alert=True)
        await state.clear()
        return
    await state.update_data(cell_id=cell_id)
    await state.set_state(PartnerOnboarding.waiting_method)
    await callback.message.answer(texts.ASK_PARTNER_METHOD, reply_markup=partner_method_kb())
    await callback.answer()


@router.callback_query(PartnerOnboarding.waiting_method, F.data == "partner_method:manual")
async def process_method_manual(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PartnerOnboarding.waiting_username_or_id)
    await callback.message.answer(texts.ASK_PARTNER_USERNAME, reply_markup=cancel_kb())
    await callback.answer()


@router.callback_query(PartnerOnboarding.waiting_method, F.data == "partner_method:code")
async def process_method_code(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data["cell_id"]
    try:
        code = await generate_invite_code(cell_id)
    except CellError as e:
        await callback.message.answer(str(e))
        await state.clear()
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer(texts.INVITE_CODE_GENERATED.format(code=code), reply_markup=remove_kb())
    await callback.answer()


@router.message(PartnerOnboarding.waiting_username_or_id, F.text)
async def process_username_or_id(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    cell_id = data["cell_id"]
    raw = message.text.strip()

    if is_telegram_id(raw):
        user = await get_user(int(raw))
    else:
        user = await get_user_by_username(normalize_username(raw))

    if user is None:
        await message.answer(texts.USER_NOT_FOUND)
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


@router.message(Command("kod_olish"), IsMentor())
@router.message(F.text == "🔑 Kod olish", IsMentor())
async def cmd_kod_olish(message: Message) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer(texts.NO_ACTIVE_CELLS_MENTOR)
        return
    if len(cells) == 1:
        try:
            code = await generate_invite_code(cells[0]["id"])
        except CellError as e:
            await message.answer(str(e))
            return
        await message.answer(texts.INVITE_CODE_GENERATED.format(code=code))
        return
    from keyboards.inline import cells_kb as _cells_kb

    await message.answer(texts.ASK_CELL_FOR_PARTNER, reply_markup=_cells_kb(cells, "kod_cell"))


@router.callback_query(F.data.startswith("kod_cell:"))
async def cb_kod_cell(callback: CallbackQuery) -> None:
    cell_id = int(callback.data.split(":")[1])
    try:
        await assert_mentor_owns_cell(callback.from_user.id, cell_id)
        code = await generate_invite_code(cell_id)
    except CellError as e:
        await callback.message.answer(str(e))
        await callback.answer()
        return
    await callback.message.answer(texts.INVITE_CODE_GENERATED.format(code=code))
    await callback.answer()


@router.message(Command("qoshilish"))
async def cmd_join_by_code(message: Message, command: CommandObject, state: FSMContext) -> None:
    if command.args and is_valid_invite_code(command.args.strip()):
        await _try_join(message, command.args.strip())
        return
    await state.set_state(JoinByCode.waiting_code)
    await message.answer(texts.ASK_INVITE_CODE, reply_markup=cancel_kb())


@router.message(JoinByCode.waiting_code, F.text)
async def process_join_code(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not is_valid_invite_code(raw):
        await message.answer("Kod 6 xonali raqam bo'lishi kerak. Qayta urinib ko'ring.")
        return
    await state.clear()
    await _try_join(message, raw)


async def _try_join(message: Message, code: str) -> None:
    cell = await find_cell_by_invite_code(code)
    if cell is None:
        await message.answer(texts.INVITE_CODE_INVALID, reply_markup=remove_kb())
        return
    try:
        await add_partner(cell["id"], message.from_user.id)
    except CellError as e:
        await message.answer(str(e), reply_markup=remove_kb())
        return
    await consume_invite_code(cell["id"])
    direction = await get_direction(cell["direction_id"])
    mentor = await get_user(cell["mentor_id"])
    await message.answer(
        texts.INVITE_CODE_USED_SUCCESS.format(
            direction_name=direction["name"],
            mentor_name=mentor["full_name"],
        ),
        reply_markup=remove_kb(),
    )


@router.message(Command("partnerlarim"), IsMentor())
@router.message(F.text == "👥 Partnerlarim", IsMentor())
async def cmd_my_partners(message: Message) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer(texts.NO_ACTIVE_CELLS_MENTOR)
        return
    any_partner = False
    for cell in cells:
        partners = await list_cell_partners(cell["id"])
        if not partners:
            await message.answer(f"📚 {cell['direction_name']}: {texts.NO_PARTNERS_YET}")
            continue
        any_partner = True
        await message.answer(
            f"📚 {cell['direction_name']} hujayrasi. Profilini ko'rish uchun a'zoni tanlang:",
            reply_markup=mentor_partners_list_kb(partners, cell["id"]),
        )
    if not any_partner:
        return


async def _assert_mentor_owns_cell_or_alert(callback: CallbackQuery, cell_id: int) -> bool:
    cells = await list_cells_for_mentor(callback.from_user.id)
    if not any(c["id"] == cell_id for c in cells):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return False
    return True


async def _render_mentor_partner_profile(callback: CallbackQuery, cell_id: int, partner_id: int) -> None:
    from database.repo_v2 import sum_points_for_user
    from database.repo_tasks import count_completed_submissions

    user = await get_user(partner_id)
    if user is None:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return
    total_points = await sum_points_for_user(partner_id)
    completed = await count_completed_submissions(partner_id)
    uname = f"@{user['username']}" if user["username"] else "—"
    text = (
        f"👤 <b>{user['full_name']}</b>\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: {uname}\n\n"
        f"📊 <b>Statistika</b>\n"
        f"🏆 Jami ball: {total_points}\n"
        f"✅ Bajarilgan vazifalar: {completed}"
    )
    await callback.message.answer(text, reply_markup=mentor_partner_profile_kb(cell_id, partner_id))


@router.callback_query(F.data.startswith("mp_profile:"), IsMentor())
async def cb_mentor_partner_profile(callback: CallbackQuery) -> None:
    _, cell_id_str, partner_id_str = callback.data.split(":")
    cell_id, partner_id = int(cell_id_str), int(partner_id_str)
    if not await _assert_mentor_owns_cell_or_alert(callback, cell_id):
        return
    await _render_mentor_partner_profile(callback, cell_id, partner_id)
    await callback.answer()


@router.callback_query(F.data.startswith("mp_back:"), IsMentor())
async def cb_mentor_partner_back(callback: CallbackQuery) -> None:
    cell_id = int(callback.data.split(":")[1])
    if not await _assert_mentor_owns_cell_or_alert(callback, cell_id):
        return
    partners = await list_cell_partners(cell_id)
    if not partners:
        await callback.message.answer(texts.NO_PARTNERS_YET)
        await callback.answer()
        return
    await callback.message.answer(
        "A'zoni tanlang:",
        reply_markup=mentor_partners_list_kb(partners, cell_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mp_kick:"), IsMentor())
async def cb_mentor_partner_kick(callback: CallbackQuery) -> None:
    from database.repo_cells import remove_partner as _remove_partner

    _, cell_id_str, partner_id_str = callback.data.split(":")
    cell_id, partner_id = int(cell_id_str), int(partner_id_str)
    if not await _assert_mentor_owns_cell_or_alert(callback, cell_id):
        return
    user = await get_user(partner_id)
    await _remove_partner(cell_id, partner_id)
    await callback.message.answer(texts.PARTNER_REMOVED.format(partner_name=user["full_name"] if user else partner_id))
    await callback.answer()


@router.callback_query(F.data.startswith("mp_move:"), IsMentor())
async def cb_mentor_partner_move_pick_target(callback: CallbackQuery, state: FSMContext) -> None:
    _, cell_id_str, partner_id_str = callback.data.split(":")
    cell_id, partner_id = int(cell_id_str), int(partner_id_str)
    if not await _assert_mentor_owns_cell_or_alert(callback, cell_id):
        return
    cells = await list_cells_for_mentor(callback.from_user.id)
    if len(cells) <= 1:
        await callback.answer("Boshqa faol guruhingiz yo'q.", show_alert=True)
        return
    await state.update_data(mp_from_cell_id=cell_id, mp_partner_id=partner_id)
    await callback.message.answer(
        "Qaysi guruhingizga o'tkazmoqchisiz?",
        reply_markup=mentor_move_target_cells_kb(cells, cell_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mp_move_to:"), IsMentor())
async def cb_mentor_partner_move_to(callback: CallbackQuery, state: FSMContext) -> None:
    from database.repo_cells import move_partner_to_cell

    to_cell_id = int(callback.data.split(":")[1])
    if not await _assert_mentor_owns_cell_or_alert(callback, to_cell_id):
        await state.clear()
        return
    data = await state.get_data()
    from_cell_id = data.get("mp_from_cell_id")
    partner_id = data.get("mp_partner_id")
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
    await callback.message.answer("✅ A'zo boshqa guruhga o'tkazildi.")
    await callback.answer()
