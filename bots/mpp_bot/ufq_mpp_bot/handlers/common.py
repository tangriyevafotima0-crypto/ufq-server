from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.repo_cells import (
    CellError,
    add_partner,
    get_cell_for_join_link,
    list_cells_for_mentor,
)
from database.repo_directions import get_direction
from database.repo_quotas import MAX_CELLS_AS_PARTNER, QuotaError, assert_can_join_as_partner
from database.repo_users import get_user, is_admin
from keyboards.reply import admin_menu_kb, mentor_menu_kb, partner_menu_kb, remove_kb
from utils.texts import BTN_CANCEL, CANCELLED, WELCOME

router = Router(name="common")


async def send_role_menu(message: Message) -> None:
    uid = message.from_user.id
    admin = await is_admin(uid)
    cells = await list_cells_for_mentor(uid)

    if admin:
        await message.answer("🛡 Siz administratorsiz.", reply_markup=admin_menu_kb())
        return

    if cells:
        await message.answer(
            "🧑‍🏫 Siz quyidagi yo'nalish(lar)da mentorsiz: "
            + ", ".join(c["direction_name"] for c in cells),
            reply_markup=mentor_menu_kb(),
        )
        return

    await message.answer(
        "Siz hozircha partner sifatida ro'yxatdan o'tgansiz.",
        reply_markup=partner_menu_kb(),
    )


async def _handle_join_deep_link(message: Message, cell_id: int) -> None:
    uid = message.from_user.id
    cell = await get_cell_for_join_link(cell_id)
    if cell is None:
        await message.answer("❌ Ushbu taklif havolasi endi amal qilmaydi (guruh topilmadi yoki arxivlangan).")
        return
    try:
        await assert_can_join_as_partner(uid, cell_id)
    except QuotaError as e:
        await message.answer(f"❌ {e}")
        return
    try:
        await add_partner(cell_id, uid)
    except CellError as e:
        await message.answer(f"❌ {e}")
        return
    direction = await get_direction(cell["direction_id"])
    mentor = await get_user(cell["mentor_id"]) if cell["mentor_id"] else None
    mentor_label = mentor["full_name"] if mentor else "mentor yo'q (peer-to-peer)"
    await message.answer(
        f"✅ Siz \"{direction['name']}\" yo'nalishidagi {mentor_label} guruhiga muvaffaqiyatli qo'shildingiz!"
    )
    if mentor:
        from services.notifier import safe_send

        await safe_send(
            mentor["telegram_id"],
            f"👋 {message.from_user.full_name} taklif havolasi orqali guruhingizga qo'shildi.",
        )


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME.format(name=message.from_user.full_name))
    payload = (command.args or "").strip()
    if payload.startswith("join_"):
        cell_id_str = payload[len("join_"):]
        if cell_id_str.isdigit():
            await _handle_join_deep_link(message, int(cell_id_str))
    await send_role_menu(message)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME.format(name=message.from_user.full_name))
    await send_role_menu(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_role_menu(message)


@router.message(F.text == BTN_CANCEL)
@router.message(Command("bekor"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Bekor qilinadigan hech narsa yo'q.", reply_markup=remove_kb())
        return
    await state.clear()
    await message.answer(CANCELLED, reply_markup=remove_kb())
    await send_role_menu(message)
