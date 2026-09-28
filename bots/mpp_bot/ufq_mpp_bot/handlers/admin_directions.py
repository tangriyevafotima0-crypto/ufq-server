from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.repo_directions import (
    create_direction,
    direction_name_exists,
    list_directions,
    toggle_direction,
)
from handlers.states import DirectionCreation
from keyboards.reply import cancel_kb, remove_kb
from middlewares.access import IsAdmin
from utils import texts

router = Router(name="admin_directions")
router.message.filter(IsAdmin())


def _directions_menu_kb(directions):
    builder = InlineKeyboardBuilder()
    for d in directions:
        status = "✅" if d["is_active"] else "⛔️"
        builder.button(text=f"{status} {d['name']}", callback_data=f"toggle_dir:{d['id']}")
    builder.button(text="➕ Yangi yo'nalish qo'shish", callback_data="new_direction")
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("yonalishlar"))
@router.message(F.text == "📚 Yo'nalishlar")
async def cmd_directions(message: Message) -> None:
    directions = await list_directions()
    if not directions:
        await message.answer(texts.DIRECTIONS_EMPTY, reply_markup=_directions_menu_kb([]))
        return
    await message.answer(texts.DIRECTIONS_LIST_HEADER, reply_markup=_directions_menu_kb(directions))


@router.callback_query(F.data == "new_direction")
async def cb_new_direction(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DirectionCreation.waiting_name)
    await callback.message.answer(texts.ASK_DIRECTION_NAME, reply_markup=cancel_kb())
    await callback.answer()


@router.message(DirectionCreation.waiting_name, F.text)
async def process_direction_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if await direction_name_exists(name):
        await message.answer(texts.DIRECTION_ALREADY_EXISTS)
        return
    await create_direction(name)
    await state.clear()
    await message.answer(texts.DIRECTION_CREATED.format(name=name), reply_markup=remove_kb())


@router.callback_query(F.data.startswith("toggle_dir:"))
async def cb_toggle_direction(callback: CallbackQuery) -> None:
    direction_id = int(callback.data.split(":")[1])
    await toggle_direction(direction_id)
    directions = await list_directions()
    try:
        await callback.message.edit_text(texts.DIRECTIONS_LIST_HEADER, reply_markup=_directions_menu_kb(directions))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer("Holat yangilandi")
