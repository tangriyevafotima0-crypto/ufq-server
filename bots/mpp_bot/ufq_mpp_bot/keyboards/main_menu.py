from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

def get_persistent_reply_keyboard(is_admin: bool = False, is_mentor: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📋 Vazifalarim"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🔑 Kod bilan qo'shilish"), KeyboardButton(text="📱 Asosiy menyu")]
    ]
    if is_mentor or is_admin:
        keyboard.append([KeyboardButton(text="➕ Vazifa berish"), KeyboardButton(text="👥 Partnerlarim")])
        keyboard.append([KeyboardButton(text="🎯 Mock kiritish"), KeyboardButton(text="⏳ Muddat uzaytirish")])
    if is_admin:
        keyboard.append([KeyboardButton(text="📚 Yo'nalishlar"), KeyboardButton(text="🎓 Mentor tayinlash")])
        keyboard.append([KeyboardButton(text="⚙️ Hujayralar nazorati"), KeyboardButton(text="📈 Oylik hisobot")])
        
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)

def get_main_inline_menu(is_admin: bool = False, is_mentor: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📋 Vazifalarim (/holat)", callback_data="btn_tasks_status"),
            InlineKeyboardButton(text="📊 Statistika (/statistika)", callback_data="btn_my_stats")
        ],
        [
            InlineKeyboardButton(text="🔑 Kod bilan qo'shilish", callback_data="btn_join_by_code")
        ]
    ]
    if is_mentor or is_admin:
        buttons.append([
            InlineKeyboardButton(text="➕ Yangi vazifa berish", callback_data="btn_give_task"),
            InlineKeyboardButton(text="👥 Partnerlarim", callback_data="btn_my_partners")
        ])
        buttons.append([
            InlineKeyboardButton(text="🎯 Mock ball kiritish", callback_data="btn_enter_mock"),
            InlineKeyboardButton(text="⏳ Muddat uzaytirish", callback_data="btn_extend_deadline")
        ])
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="📚 Yo'nalishlar", callback_data="btn_admin_dirs"),
            InlineKeyboardButton(text="🎓 Mentor tayinlash", callback_data="btn_admin_mentor")
        ])
        buttons.append([
            InlineKeyboardButton(text="⚙️ Hujayralar nazorati", callback_data="btn_admin_manage"),
            InlineKeyboardButton(text="📈 Oylik hisobot", callback_data="btn_admin_report")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
