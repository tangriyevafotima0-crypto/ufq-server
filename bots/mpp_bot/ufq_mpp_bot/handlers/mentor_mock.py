from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repo_cells import list_cell_partners, list_cells_for_mentor
from database.repo_misc import add_mock_result
from handlers.states import MockEntry
from keyboards.inline import cells_kb, partners_kb
from keyboards.reply import cancel_kb, remove_kb
from middlewares.access import IsMentor
from utils import texts
from utils.validators import validate_date_input, validate_score_input

router = Router(name="mentor_mock")


@router.message(Command("mock_kirit"), IsMentor())
@router.message(F.text == "🎯 Mock kiritish", IsMentor())
async def cmd_mock_entry(message: Message, state: FSMContext) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer(texts.NO_ACTIVE_CELLS_MENTOR)
        return
    if len(cells) == 1:
        await state.update_data(cell_id=cells[0]["id"], direction_id=cells[0]["direction_id"])
        partners = await list_cell_partners(cells[0]["id"])
        if not partners:
            await message.answer(texts.NO_PARTNERS_YET)
            await state.clear()
            return
        await state.set_state(MockEntry.waiting_partner)
        await message.answer(texts.ASK_PARTNER_FOR_MOCK, reply_markup=partners_kb(partners, "mock_partner"))
        return
    await state.set_state(MockEntry.waiting_cell)
    await message.answer(texts.ASK_CELL_FOR_TASK, reply_markup=cells_kb(cells, "mock_cell"))


@router.callback_query(MockEntry.waiting_cell, F.data.startswith("mock_cell:"))
async def process_mock_cell(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    partners = await list_cell_partners(cell_id)
    if not partners:
        await callback.message.answer(texts.NO_PARTNERS_YET)
        await state.clear()
        await callback.answer()
        return
    cell_row = None
    for c in await list_cells_for_mentor(callback.from_user.id):
        if c["id"] == cell_id:
            cell_row = c
            break
    await state.update_data(cell_id=cell_id, direction_id=cell_row["direction_id"] if cell_row else None)
    await state.set_state(MockEntry.waiting_partner)
    await callback.message.answer(texts.ASK_PARTNER_FOR_MOCK, reply_markup=partners_kb(partners, "mock_partner"))
    await callback.answer()


@router.callback_query(MockEntry.waiting_partner, F.data.startswith("mock_partner:"))
async def process_mock_partner(callback: CallbackQuery, state: FSMContext) -> None:
    partner_id = int(callback.data.split(":")[1])
    await state.update_data(partner_id=partner_id)
    await state.set_state(MockEntry.waiting_score)
    data = await state.get_data()
    prompt = texts.ASK_MOCK_SCORE
    if data.get("direction_id") is not None:
        from database.repo_directions import get_direction

        direction = await get_direction(data["direction_id"])
        if direction:
            dname = direction["name"].strip().upper()
            if dname == "IELTS":
                prompt = "Test ballini kiriting (IELTS, 0.0–9.0, 0.5 qadam bilan, masalan: 6.5):"
            elif "SAT" in dname and ("MATH" in dname or "READING" in dname or "WRITING" in dname):
                prompt = "Test ballini kiriting (SAT bo'lim, 200–800, 10 qadam bilan, masalan: 650):"
            elif dname == "SAT":
                prompt = "Test ballini kiriting (SAT, 400–1600, 10 qadam bilan, masalan: 1200):"
    await callback.message.answer(prompt, reply_markup=cancel_kb())
    await callback.answer()


@router.message(MockEntry.waiting_score, F.text)
async def process_mock_score(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    direction_name = None
    if data.get("direction_id") is not None:
        from database.repo_directions import get_direction

        direction = await get_direction(data["direction_id"])
        direction_name = direction["name"] if direction else None
    ok, err, score = validate_score_input(message.text, direction_name)
    if not ok:
        await message.answer(err)
        return
    await state.update_data(score=score)
    await state.set_state(MockEntry.waiting_date)
    await message.answer(texts.ASK_MOCK_DATE, reply_markup=cancel_kb())


@router.message(MockEntry.waiting_date, F.text)
async def process_mock_date(message: Message, state: FSMContext) -> None:
    ok, err = validate_date_input(message.text)
    if not ok:
        await message.answer(err)
        return
    date_str = message.text.strip()
    data = await state.get_data()
    from database.repo_users import get_user

    partner = await get_user(data["partner_id"])
    await add_mock_result(
        user_id=data["partner_id"],
        direction_id=data["direction_id"],
        entered_by=message.from_user.id,
        score=data["score"],
        date_str=date_str,
    )
    await state.clear()
    await message.answer(
        texts.MOCK_SAVED.format(full_name=partner["full_name"], score=data["score"], date=date_str),
        reply_markup=remove_kb(),
    )
