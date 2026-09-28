"""Centralized Uzbek (Latin) localization strings for the UFQ MPP Bot."""

WELCOME = (
    "Assalomu alaykum, {name}! 👋\n\n"
    "UFQ MPP (Mentor-Partner-Partner) botiga xush kelibsiz.\n"
    "Bu bot orqali vazifalaringizni kuzatib borishingiz, mock natijalaringizni "
    "ko'rishingiz va o'z hujayrangiz bilan muloqot qilishingiz mumkin."
)

NOT_ADMIN = "Kechirasiz, bu buyruq faqat administrator uchun mavjud."
NOT_MENTOR = "Kechirasiz, bu buyruq faqat mentorlar uchun mavjud."
NO_ACTIVE_CELLS_MENTOR = "Sizga hali hech qanday hujayra biriktirilmagan."
GENERIC_ERROR = "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring yoki /start bosing."
CANCELLED = "Amal bekor qilindi."

# ---------- Directions (admin) ----------
DIRECTIONS_LIST_HEADER = "📚 Yo'nalishlar ro'yxati:"
DIRECTIONS_EMPTY = "Hozircha hech qanday yo'nalish yaratilmagan."
ASK_DIRECTION_NAME = "Yangi yo'nalish nomini kiriting (masalan: IELTS Writing):"
DIRECTION_ALREADY_EXISTS = "Bu nomdagi yo'nalish allaqachon mavjud."
DIRECTION_CREATED = "✅ Yo'nalish yaratildi: {name}"
DIRECTION_TOGGLED = "Holat yangilandi: {name} -> {status}"

# ---------- Mentor assignment (admin) ----------
ASK_DIRECTION_FOR_MENTOR = "Mentor tayinlash uchun yo'nalishni tanlang:"
ASK_MENTOR_USER = (
    "Mentor etib tayinlanadigan foydalanuvchini tanlang, "
    "yoki uning Telegram ID raqamini yuboring:"
)
MENTOR_ASSIGNED = "✅ {mentor_name} endi \"{direction_name}\" yo'nalishida mentor."
MENTOR_ALREADY_ASSIGNED = "Bu foydalanuvchi ushbu yo'nalishda allaqachon mentor."
USER_NOT_FOUND = "Foydalanuvchi topilmadi. U botga /start orqali kirishi kerak."

# ---------- Partner onboarding ----------
ASK_CELL_FOR_PARTNER = "Qaysi hujayraga partner qo'shmoqchisiz?"
ASK_PARTNER_METHOD = "Partnerni qanday qo'shmoqchisiz?"
ASK_PARTNER_USERNAME = "Partnerning @username yoki Telegram ID raqamini yuboring:"
PARTNER_ADDED = "✅ {partner_name} hujayrangizga partner sifatida qo'shildi."
CELL_FULL = "❌ Hujayrada eng ko'pi bilan 3 ta partner bo'lishi mumkin. Joy yo'q."
SELF_MENTOR_BLOCK = "❌ Mentor o'zini o'z hujayrasiga partner sifatida qo'sha olmaydi."
ALREADY_PARTNER = "Bu foydalanuvchi allaqachon ushbu hujayrada partner."

INVITE_CODE_GENERATED = (
    "🔑 Taklif kodi: <code>{code}</code>\n\n"
    "Bu kod 24 soat davomida amal qiladi va faqat bir marta ishlatilishi mumkin.\n"
    "Partneringizga quyidagi buyruqni yuborishni ayting:\n"
    "<code>/qoshilish {code}</code>"
)
INVITE_CODE_INVALID = "❌ Kod noto'g'ri yoki muddati o'tgan."
INVITE_CODE_USED_SUCCESS = "✅ Siz \"{direction_name}\" yo'nalishidagi {mentor_name} hujayrasiga muvaffaqiyatli qo'shildingiz!"
ASK_INVITE_CODE = "Hujayraga qo'shilish uchun kodni kiriting:\n<code>/qoshilish 123456</code>"

# ---------- Partner list / removal ----------
MY_PARTNERS_HEADER = "👥 Sizning partnerlaringiz:"
NO_PARTNERS_YET = "Hozircha hech qanday partneringiz yo'q."
PARTNER_REMOVED = "❌ {partner_name} hujayradan chiqarildi."

# ---------- Tasks ----------
ASK_CELL_FOR_TASK = "Qaysi hujayra uchun vazifa yaratmoqchisiz?"
ASK_TASK_TITLE = "Vazifa sarlavhasini kiriting:"
ASK_TASK_DESCRIPTION = "Vazifa tavsifini kiriting (yoki \"-\" deb yozing, agar tavsif bo'lmasa):"
ASK_TASK_DEADLINE = "Muddatni kiriting (format: YYYY-MM-DD HH:MM), masalan: 2026-09-15 18:00"
TASK_CREATED = (
    "✅ Vazifa yaratildi!\n\n"
    "📌 <b>{title}</b>\n"
    "📝 {description}\n"
    "⏰ Muddat: {deadline}\n"
    "👥 {partner_count} ta partnerga yuborildi."
)
NO_PARTNERS_FOR_TASK = "Bu hujayrada hozircha faol partner yo'q, vazifa yaratib bo'lmaydi."

ASK_TASK_FOR_DEADLINE_CHANGE = "Muddatini o'zgartirmoqchi bo'lgan vazifani tanlang:"
ASK_NEW_DEADLINE = "Yangi muddatni kiriting (format: YYYY-MM-DD HH:MM):"
DEADLINE_UPDATED = "✅ Muddat yangilandi: {deadline}"
NO_ACTIVE_TASKS = "Faol vazifalar mavjud emas."

# ---------- Partner status ----------
MY_STATUS_HEADER = "📋 Sizning faol vazifalaringiz:"
NO_ACTIVE_TASKS_PARTNER = "Sizda hozircha faol vazifalar yo'q. 🎉"
TASK_STATUS_UPDATED = "✅ Holat yangilandi: {status}"
STATUS_LABELS = {
    "kutilmoqda": "⏳ Kutilmoqda",
    "jarayonda": "🔄 Jarayonda",
    "bajardi": "✅ Bajarildi",
    "bajarmadi": "❌ Bajarilmadi",
}

# ---------- Mock results ----------
ASK_PARTNER_FOR_MOCK = "Qaysi partner uchun mock natijasini kiritmoqchisiz?"
ASK_MOCK_SCORE = "Test ballini kiriting (masalan: 6.5):"
ASK_MOCK_DATE = "Test sanasini kiriting (format: YYYY-MM-DD):"
MOCK_SAVED = "✅ Mock natija saqlandi: {full_name} — {score} ball ({date})"

# ---------- Reminders / escalation ----------
REMINDER_24H = (
    "⏰ Eslatma: \"{title}\" vazifasi uchun muddat 24 soatdan kam qoldi!\n"
    "Muddat: {deadline}"
)
REMINDER_3H = (
    "🚨 Diqqat: \"{title}\" vazifasi uchun muddat 3 soatdan kam qoldi!\n"
    "Muddat: {deadline}"
)
CHECKIN_3DAY = (
    "👋 Salom! Sizda ochiq vazifalar bor. Jarayoningiz qanday ketyapti?\n"
    "\"{title}\" — muddat: {deadline}"
)
CHECKIN_3DAY_MULTI_HEADER = "👋 Salom! Sizda {count} ta faol vazifa bor. Jarayoningiz qanday ketyapti?"
CHECKIN_3DAY_MULTI_ROW = "{index}) \"{title}\" — muddat: {deadline}"
OVERDUE_MENTOR_ALERT = (
    "⚠️ \"{title}\" vazifasi bo'yicha muddat o'tdi.\n"
    "Quyidagi partnerlar hali vazifani bajarmagan:\n{names}"
)
TASK_OVERDUE_PARTNER = "❌ \"{title}\" vazifasi bo'yicha muddat o'tdi va vazifa bajarilmagan deb belgilandi."

# ---------- Statistics ----------
STATS_HEADER = "📊 Sizning statistikangiz:"
STATS_ROW = "{status_emoji} {title} — {status}"
COMPARATIVE_HEADER = "\n👥 Hujayra bo'yicha taqqoslash:"
COMPARATIVE_ROW = "{name}: {completed}/{total} bajarilgan ({pct:.0f}%)"

# ---------- Admin reports ----------
REPORT_GENERATING = "📊 Hisobot tayyorlanmoqda..."
REPORT_HEADER = "📊 <b>Umumiy hisobot</b> ({date})\n"

MONTHLY_REPORT_CAPTION = "📊 Oylik hisobot — {month}"
MONTHLY_SUMMARY_CARD = (
    "📬 <b>Oylik shaxsiy hisobot</b> — {month}\n\n"
    "✅ Bajarilgan vazifalar: {done}\n"
    "❌ Bajarilmagan vazifalar: {failed}\n"
    "⏳ Jarayondagi vazifalar: {pending}\n"
    "📈 Bajarish foizi: {pct:.0f}%\n"
)

# ---------- Cancel keyboard ----------
BTN_CANCEL = "❌ Bekor qilish"
BTN_BACK = "⬅️ Orqaga"
