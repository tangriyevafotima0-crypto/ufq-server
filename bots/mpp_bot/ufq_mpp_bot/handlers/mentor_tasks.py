from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repo_cells import assert_mentor_owns_cell, list_cell_partners, list_cells_for_mentor
from database.repo_tasks import create_task, get_task, list_active_tasks_for_cell, update_task_deadline
from handlers.states import DeadlineExtension, TaskCreation
from keyboards.inline import cells_kb, tasks_kb
from keyboards.reply import cancel_kb, remove_kb
from middlewares.access import IsMentor
from services.scheduler import schedule_task_reminders, reschedule_task_reminders
from database.repo_cells import CellError
from utils import texts
from utils.timez import humanize, to_db_str
from utils.validators import validate_deadline_input

router = Router(name="mentor_tasks")


@router.message(Command("vazifa_ber"), IsMentor())
@router.message(F.text == "📌 Vazifa berish", IsMentor())
async def cmd_create_task(message: Message, state: FSMContext) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    if not cells:
        await message.answer(texts.NO_ACTIVE_CELLS_MENTOR)
        return
    await state.set_state(TaskCreation.waiting_cell)
    await message.answer(texts.ASK_CELL_FOR_TASK, reply_markup=cells_kb(cells, "task_cell"))


@router.callback_query(TaskCreation.waiting_cell, F.data.startswith("task_cell:"))
async def process_task_cell(callback: CallbackQuery, state: FSMContext) -> None:
    cell_id = int(callback.data.split(":")[1])
    try:
        await assert_mentor_owns_cell(callback.from_user.id, cell_id)
    except CellError as e:
        await callback.answer(str(e), show_alert=True)
        await state.clear()
        return
    partners = await list_cell_partners(cell_id)
    if not partners:
        await callback.message.answer(texts.NO_PARTNERS_FOR_TASK)
        await state.clear()
        await callback.answer()
        return
    await state.update_data(cell_id=cell_id)
    await state.set_state(TaskCreation.waiting_title)
    await callback.message.answer(texts.ASK_TASK_TITLE, reply_markup=cancel_kb())
    await callback.answer()


@router.message(TaskCreation.waiting_title, F.text)
async def process_task_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(TaskCreation.waiting_description)
    await message.answer(texts.ASK_TASK_DESCRIPTION, reply_markup=cancel_kb())


@router.message(TaskCreation.waiting_description, F.text)
async def process_task_description(message: Message, state: FSMContext) -> None:
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    await state.update_data(description=desc)
    await state.set_state(TaskCreation.waiting_deadline)
    await message.answer(texts.ASK_TASK_DEADLINE, reply_markup=cancel_kb())


@router.message(TaskCreation.waiting_deadline, F.text)
async def process_task_deadline(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    ok, err = validate_deadline_input(raw)
    if not ok:
        await message.answer(err)
        return
    from utils.timez import parse_deadline

    dt = parse_deadline(raw)
    deadline_db = to_db_str(dt)

    data = await state.get_data()
    task_id = await create_task(
        cell_id=data["cell_id"],
        created_by=message.from_user.id,
        title=data["title"],
        description=data.get("description", ""),
        deadline_str=deadline_db,
    )
    await schedule_task_reminders(task_id, dt)

    partners = await list_cell_partners(data["cell_id"])
    await state.clear()
    await message.answer(
        texts.TASK_CREATED.format(
            title=data["title"],
            description=data.get("description") or "—",
            deadline=humanize(deadline_db),
            partner_count=len(partners),
        ),
        reply_markup=remove_kb(),
    )

    from services.notifier import notify_task_assigned

    unreachable = await notify_task_assigned(task_id, partners, data["title"], data.get("description", ""), deadline_db)
    if unreachable:
        names = ", ".join(p["full_name"] for p in unreachable)
        await message.answer(
            f"⚠️ Quyidagi partner(lar) hali botni ishga tushirmagan, shuning uchun ularga bildirishnoma "
            f"yubora olmadim: {names}. Iltimos, ularga bot havolasini yuboring."
        )


@router.message(Command("deadline_uzaytir"), IsMentor())
@router.message(F.text == "⏰ Muddatni uzaytirish", IsMentor())
async def cmd_extend_deadline(message: Message, state: FSMContext) -> None:
    cells = await list_cells_for_mentor(message.from_user.id)
    all_tasks = []
    for c in cells:
        tasks = await list_active_tasks_for_cell(c["id"])
        all_tasks.extend(tasks)
    if not all_tasks:
        await message.answer(texts.NO_ACTIVE_TASKS)
        return
    await state.set_state(DeadlineExtension.waiting_task)
    await message.answer(texts.ASK_TASK_FOR_DEADLINE_CHANGE, reply_markup=tasks_kb(all_tasks, "ext_task"))


@router.callback_query(DeadlineExtension.waiting_task, F.data.startswith("ext_task:"))
async def process_extend_task_choice(callback: CallbackQuery, state: FSMContext) -> None:
    task_id = int(callback.data.split(":")[1])
    task = await get_task(task_id)
    if task is None:
        await callback.answer("Vazifa topilmadi.", show_alert=True)
        await state.clear()
        return
    try:
        await assert_mentor_owns_cell(callback.from_user.id, task["cell_id"])
    except CellError as e:
        await callback.answer(str(e), show_alert=True)
        await state.clear()
        return
    await state.update_data(task_id=task_id)
    await state.set_state(DeadlineExtension.waiting_new_deadline)
    await callback.message.answer(texts.ASK_NEW_DEADLINE, reply_markup=cancel_kb())
    await callback.answer()


@router.message(DeadlineExtension.waiting_new_deadline, F.text)
async def process_new_deadline(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    ok, err = validate_deadline_input(raw)
    if not ok:
        await message.answer(err)
        return
    from utils.timez import parse_deadline

    dt = parse_deadline(raw)
    deadline_db = to_db_str(dt)
    data = await state.get_data()
    task_id = data["task_id"]
    await update_task_deadline(task_id, deadline_db)
    await reschedule_task_reminders(task_id, dt)
    await state.clear()
    await message.answer(texts.DEADLINE_UPDATED.format(deadline=humanize(deadline_db)), reply_markup=remove_kb())
