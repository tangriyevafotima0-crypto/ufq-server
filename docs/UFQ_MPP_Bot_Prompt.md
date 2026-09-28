# UFQ MPP Bot — Texnik Topshiriq (Claude Code uchun)

## Kontekst

UFQ — Qashqadaryo, Kasbi tumanidagi yoshlar tashkiloti. 14 nafar a'zo SAT/IELTS orqali chet el universitetlariga tayyorlanmoqda. Ular **Mentor-Partner-Partner (MPP)** deb nomlangan tizimda ishlaydi:

- Har bir yo'nalish (masalan, IELTS Writing yoki SAT Math) bo'yicha 3 kishilik yacheyka bor: 1 mentor + 2 partner.
- Mentor — o'sha yo'nalishda eng yuqori ball/sertifikatga ega kishi. Bitta odam bir yo'nalishda mentor, boshqa yo'nalishda partner bo'lishi mumkin (rol shaxsga emas, yo'nalishga bog'liq).
- Guruh sinxron (bir vaqtda) yig'ilmaydi. Har kim o'z vaqtida ishlaydi, lekin **muddat (deadline)ga qadar** natija ko'rsatishi shart.
- Mentor: haftalik/3 kunlik reja beradi, mock test sanasini belgilaydi, natijani kiritadi, deadline qo'yadi.
- Partner: reja asosida ishlaydi, holatini (bajardi/bajarmadi) belgilaydi, tushunmasa avval ikkinchi partnerdan, keyin mentordan so'raydi.
- Rahbar (bot egasi): faqat oylik umumiy hisobotni ko'radi, kundalik ishga aralashmaydi.

Bu — **yangi, mustaqil bot**. Mavjud UFQ team_bot/event_bot infratuzilmasiga bog'lanmaydi, ular bilan integratsiya qilinmaydi, alohida loyiha sifatida qurilishi kerak.

---

## Vazifa

Yuqoridagi MPP tizimini avtomatlashtiradigan Telegram botini qurish. Bot — tizimning "xotirasi va soatqo'ng'irog'i": u qaror qabul qilmaydi (mentor tanlash, reja tuzish — odamlar ishi), faqat quyidagilarni bajaradi:

1. Progress va ball ma'lumotini saqlash
2. Deadline yaqinlashganda avtomatik eslatma yuborish
3. So'rov bo'yicha joriy statistikani ko'rsatish (guruh ichida buyruq orqali)
4. Oy oxirida umumiy hisobot faylini rahbarga yuborish + har bir a'zoga o'z shaxsiy natijasini alohida yuborish

## Texnologiya tanlovi

Samaradorlik ustuvor mezon — quyidagi tavsiyani asos qiling, lekin loyihani boshlashdan oldin o'zingiz tekshirib, kerak bo'lsa asoslab o'zgartiring:

- **Til/framework: Python + aiogram 3.x.** Sabab: Telegram bot ekotizimida eng yetuk, ko'p misolli, tez ishga tushiriladigan, kam server resursini talab qiladigan kombinatsiya; jamoa a'zolari orasida Python'ga oid tajriba borligi ehtimoli yuqori (eski UFQ botlari ham shu stack'da).
- **Ma'lumot bazasi: SQLite (aiosqlite orqali).** Sabab: 14 kishilik, past-o'rtacha yozish tezligidagi tizim uchun alohida server (Postgres/MySQL) ortiqcha murakkablik qo'shadi; SQLite — bitta fayl, backup qilish oson (shunchaki faylni ko'chirish), WAL rejimida bir nechta yozuvchi bilan ham muammosiz ishlaydi.
- Agar Claude Code boshqa kombinatsiyani (masalan, Node.js + grammY, yoki Google Sheets backend) haqiqatan samaraliroq deb hisoblasa — buni asoslab taklif qiling, lekin final qarordan oldin foydalanuvchidan tasdiq so'rang.

**MUHIM: Hozircha faqat reja/spec tasdiqlanadi — kod yozishni boshlamang.** Avval quyidagi barcha bo'limlar bo'yicha aniq texnik reja (fayl tuzilmasi, DB sxema, buyruqlar ro'yxati) taqdim eting, foydalanuvchi tasdiqlagach kodlashga o'ting.

---

## Foydalanuvchi rollari

| Rol | Kim | Huquq |
|---|---|---|
| Admin | Bot egasi (rahbar) | Hammani ko'radi, oylik hisobot oladi, a'zo/yo'nalish/yacheyka qo'shadi-o'chiradi |
| Mentor | Yacheykada mentor bo'lgan a'zo | O'z partnerlariga vazifa/reja beradi, mock sana belgilaydi, ball kiritadi, deadline qo'yadi |
| Partner | Yacheykada partner bo'lgan a'zo | O'z holatini belgilaydi, o'z va yacheykadoshlarining statistikasini ko'radi |

Bitta odam bir nechta rolda bo'lishi mumkin (masalan, IELTS'da mentor, SAT'da partner) — bot buni foydalanuvchi ID asosida ajratishi kerak, alohida akkaunt kerak emas.

---

## Ma'lumot bazasi — kerakli jadvallar (taklif, aniqlashtiring)

- `users`: telegram_id, full_name, username
- `directions`: nomi (masalan "IELTS Writing", "SAT Math")
- `cells` (yacheyka): direction_id, mentor_id
- `cell_members`: cell_id, partner_id (har yacheykada 2 ta yozuv)
- `tasks`: cell_id, title, description, deadline, created_by (mentor)
- `submissions`: task_id, user_id, status (bajardi/bajarmadi/kutilmoqda), submitted_at
- `mock_results`: cell_id yoki user_id, direction_id, score, date, entered_by (mentor)
- `reminders_log`: qaysi eslatma qachon yuborilgani (takror yubormaslik uchun)

Bu — boshlang'ich taklif. Claude Code buni ko'rib chiqib, kerak bo'lsa qo'shimcha/soddalashtirish taklif qilsin.

---

## Asosiy funksiyalar (buyruqlar/oqim)

### Admin uchun
- Yo'nalish qo'shish/o'chirish
- Yacheyka yaratish (mentor + 2 partner tayinlash)
- `/hisobot` — istalgan vaqtda joriy umumiy holatni ko'rish
- Oylik avtomatik hisobot — belgilangan kunda (masalan har oyning 1-sanasida) avtomatik yuboriladi: (a) umumiy fayl (barcha a'zolar, barcha yo'nalishlar), (b) har bir a'zoga shaxsiy natijasi alohida xabar sifatida

### Mentor uchun
- `/vazifa_ber` — partnerlariga matnli vazifa/reja yuborish (deadline bilan)
- `/mock_kirit` — mock test natijasini (ball, sana, kim) kiritish
- `/deadline` — yangi muddat belgilash, bot avtomatik eslatma jadvalini shunga moslaydi
- O'z yacheykasi statistikasini ko'rish

### Partner uchun
- `/holat` — o'ziga berilgan vazifani "bajardim/bajarmadim" deb belgilash (masalan, har 3 kunda so'raladi yoki istalgan vaqt o'zi kiritadi)
- `/statistika` — o'z va yacheykadoshi progressini ko'rish
- Savol yuborish (agar botga oddiy matn shaklida qo'shimcha "yordam so'rash" funksiyasi kerak bo'lsa — buni qo'shish/qo'shmaslikni aniqlashtiring)

### Avtomatik (fon jarayoni)
- Deadline'dan N kun/soat oldin eslatma (N — sozlanadigan, masalan 1 kun oldin)
- Deadline o'tib ketgan, lekin holat belgilanmagan bo'lsa — mentorga ogohlantirish
- Oylik hisobot generatsiyasi va yuborilishi

---

## Ochiq savollar (Claude Code reja bosqichida foydalanuvchidan so'rasin)

1. Eslatma qanchalik oldin yuborilsin (1 kun, 2 kun, sozlanadiganmi)?
2. "Har 3 kunda holat so'raladi" — bu bot tomonidan proaktiv so'ralsinmi (bot o'zi yozadi "bajardingizmi?"), yoki partner o'zi kiritishi kerakmi?
3. Oylik hisobot fayli qanday formatda bo'lsin — Excel (.xlsx), oddiy matn, yoki PDF?
4. Bot bitta shaxs (rahbar) tomonidan boshqariladigan serverga joylashtiriladimi (VPS bormi), yoki bepul/arzon hosting variant kerakmi (masalan Railway, PythonAnywhere)?
5. Til — bot xabarlari o'zbek tilida bo'lishi kerak (tasdiqlash uchun so'rang, lekin standart shu bo'lsin).

---

## Kutilayotgan natija (bu bosqichda)

Kod emas — quyidagilarni o'z ichiga olgan **yozma reja**:
- Yakuniy texnologiya tanlovi (asoslash bilan)
- To'liq fayl/papka tuzilmasi
- Yakunlangan DB sxema (jadval, ustun, tip)
- Buyruqlar va foydalanuvchi oqimlarining to'liq ro'yxati
- Yuqoridagi "Ochiq savollar"ga javoblar (foydalanuvchidan so'rab)

Reja tasdiqlangandan keyingina kodlashga o'tiladi.
