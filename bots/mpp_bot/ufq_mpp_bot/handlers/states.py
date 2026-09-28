from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class DirectionCreation(StatesGroup):
    waiting_name = State()


class MentorAssignment(StatesGroup):
    waiting_direction = State()
    waiting_mentor = State()
    waiting_mentor_id_input = State()


class PartnerOnboarding(StatesGroup):
    waiting_cell = State()
    waiting_method = State()
    waiting_username_or_id = State()


class TaskCreation(StatesGroup):
    waiting_cell = State()
    waiting_title = State()
    waiting_description = State()
    waiting_deadline = State()


class DeadlineExtension(StatesGroup):
    waiting_task = State()
    waiting_new_deadline = State()


class MockEntry(StatesGroup):
    waiting_cell = State()
    waiting_partner = State()
    waiting_score = State()
    waiting_date = State()


class JoinByCode(StatesGroup):
    waiting_code = State()


class AdminOverride(StatesGroup):
    waiting_cell_for_add = State()
    waiting_user_for_add = State()
    waiting_cell_for_remove = State()


class DirectionRename(StatesGroup):
    waiting_name = State()


class CellRename(StatesGroup):
    waiting_name = State()


class DirectionCreateTree(StatesGroup):
    waiting_name = State()
