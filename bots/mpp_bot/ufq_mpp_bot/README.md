# UFQ MPP Bot

Production Telegram bot for UFQ's Mentor-Partner-Partner (MPP) accountability system —
built for the IELTS/SAT prep cohort in Kasbi, Qashqadaryo.

Stack: Python 3.11+, aiogram 3.x, aiosqlite (WAL), APScheduler, openpyxl.
Timezone: strictly `Asia/Tashkent`. UI language: Uzbek (Latin).

## Quick start (production, Debian/Ubuntu VPS)

```bash
git clone <this repo> ufq_mpp_bot && cd ufq_mpp_bot
sudo bash install.sh
```

The installer will prompt for your Bot Token, admin Telegram ID, and timezone,
then set up a Python venv, seed the SQLite database, and register a `systemd`
service (`ufq_mpp_bot.service`, auto-restart on failure).

## Manual / local run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit BOT_TOKEN / ADMIN_IDS
python bot.py
```

## Directory layout

```
handlers/       aiogram routers (admin, mentor, partner, common, FSM states)
services/       scheduler.py (APScheduler jobs), notifier.py, excel_export.py
database/       schema.sql, db.py (connection/pragmas), repo_*.py (query layer)
keyboards/      reply.py, inline.py keyboard builders
middlewares/    user_sync.py (auto-register users), access.py (role filters)
utils/          timez.py, validators.py, texts.py (Uzbek localization)
scripts/        seed_phase_a.py (optional Phase A bootstrap helper)
```

## Command reference

**Admin**
- `/yonalishlar` — manage directions (create / toggle active)
- `/mentor_tayinlash` — assign a mentor to a direction (creates a cell)
- `/admin_boshqaruv` — view all cells, force add/remove partners, deactivate cells
- `/hisobot` — generate the multi-tab `.xlsx` report on demand

**Mentor**
- `/partner_qosh` — add a partner (manual @username/ID, or via invite code)
- `/kod_olish` — generate a 24h single-use 6-digit invite code
- `/partnerlarim` — list partners with quick-remove buttons
- `/vazifa_ber` — task creation wizard (title → description → deadline)
- `/mock_kirit` — record a mock exam score for a partner
- `/deadline_uzaytir` — extend a task's deadline (reschedules reminders)

**Partner**
- `/qoshilish <code>` — join a cell using a mentor's invite code
- `/holat` — view active tasks with inline status buttons
- `/statistika` — personal + comparative cell completion stats

## Automated jobs (`services/scheduler.py`)

| Job | Trigger |
|---|---|
| T-24h / T-3h reminders | per-task, scheduled at creation/extension |
| Overdue escalation | at deadline: marks pending as `bajarmadi`, alerts mentor |
| Proactive check-in | every 3 days, 19:00 Asia/Tashkent |
| Monthly settlement | 1st of month, 08:00 Asia/Tashkent — `.xlsx` to admins + per-member summary cards |

On process restart, `reschedule_all_active_tasks_on_startup()` re-registers all
pending reminder/overdue jobs from the DB (jobs are not persisted across restarts
by default since `MemoryStorage`/in-process `AsyncIOScheduler` is used).

## Notes on design decisions

- **Capacity guard (max 3 partners/cell)** and **self-mentorship block** are
  enforced centrally in `database/repo_cells.py::add_partner` — both the mentor
  self-service path and the admin override path call this same function, so the
  invariant can't be bypassed from either route.
- **Invite codes** are 6-digit, single-use (cleared via `consume_invite_code`
  immediately on successful join), and expire after 24h (checked against
  `Asia/Tashkent` time at lookup).
- **Track-scoped roles**: a `cells` row binds one mentor to one direction; a user
  can appear as `mentor_id` on one cell and as a `cell_members.partner_id` on a
  different cell (different direction) simultaneously — no schema change needed.
