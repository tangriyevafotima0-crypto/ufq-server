from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repo_cells import CellError, create_cell
from database.repo_directions import get_direction, list_directions
from database.repo_users import get_user, list_all_users
from handlers.states import MentorAssignment
from keyboards.inline import directions_kb, users_kb
from keyboards.reply import cancel_kb, remove_kb
from middlewares.access import IsAdmin
from utils import texts

router = Router(name="admin_mentor")
router.message.filter(IsAdmin())


@router.message(Command("mentor_tayinlash"))
@router.message(F.text == "🧑‍🏫 Mentor tayinlash")
async def cmd_assign_mentor(message: Message, state: FSMContext) -> None:
    directions = await list_directions(active_only=True)
    if not directions:
        await message.answer("Avval yo'nalish yarating (/yonalishlar).")
        return
    await state.set_state(MentorAssignment.waiting_direction)
    await message.answer(texts.ASK_DIRECTION_FOR_MENTOR, reply_markup=directions_kb(directions, "assign_dir"))


@router.callback_query(MentorAssignment.waiting_direction, F.data.startswith("assign_dir:"))
async def process_direction_choice(callback: CallbackQuery, state: FSMContext) -> None:
    direction_id = int(callback.data.split(":")[1])
    await state.update_data(direction_id=direction_id)
    await state.set_state(MentorAssignment.waiting_mentor)
    users = await list_all_users()
    await callback.message.answer(
        texts.ASK_MENTOR_USER,
        reply_markup=users_kb(users, "assign_mentor") if users else None,
    )
    await callback.answer()


@router.callback_query(MentorAssignment.waiting_mentor, F.data.startswith("assign_mentor:"))
async def process_mentor_choice_callback(callback: CallbackQuery, state: FSMContext) -> None:
    mentor_id = int(callback.data.split(":")[1])
    await _finalize_mentor_assignment(callback.message, state, mentor_id)
    await callback.answer()


@router.message(MentorAssignment.waiting_mentor, F.text)
async def process_mentor_choice_text(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("Iltimos, ro'yxatdan tanlang yoki Telegram ID raqamini yuboring.")
        return
    await _finalize_mentor_assignment(message, state, int(raw))


async def _finalize_mentor_assignment(message: Message, state: FSMContext, mentor_id: int) -> None:
    data = await state.get_data()
    direction_id = data["direction_id"]
    user = await get_user(mentor_id)
    if user is None:
        await message.answer(texts.USER_NOT_FOUND)
        return
    direction = await get_direction(direction_id)
    try:
        await create_cell(direction_id, mentor_id)
    except CellError as e:
        await message.answer(str(e))
        return
    await state.clear()
    await message.answer(
        texts.MENTOR_ASSIGNED.format(mentor_name=user["full_name"], direction_name=direction["name"]),
        reply_markup=remove_kb(),
    )
