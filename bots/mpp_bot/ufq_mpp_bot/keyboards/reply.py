from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from utils.texts import BTN_CANCEL


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Guruh ochish va a'zolarni biriktirish")],
            [KeyboardButton(text="📊 Hisobot")],
        ],
        resize_keyboard=True,
    )


def mentor_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Partner qo'shish"), KeyboardButton(text="👥 Partnerlarim")],
            [KeyboardButton(text="📌 Vazifa berish"), KeyboardButton(text="🎯 Mock kiritish")],
            [KeyboardButton(text="⏰ Muddatni uzaytirish"), KeyboardButton(text="🔑 Kod olish")],
        ],
        resize_keyboard=True,
    )


def partner_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Holatim"), KeyboardButton(text="📊 Statistikam")],
            [KeyboardButton(text="🔑 Kod bilan qo'shilish"), KeyboardButton(text="🌐 Guruhlar ro'yxati")],
        ],
        resize_keyboard=True,
    )
