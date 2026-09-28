from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from config import config
from database.repo_misc import has_reminder_been_sent, log_reminder
from database.repo_tasks import (
    close_task,
    get_task,
    list_all_active_tasks,
    list_pending_submissions_for_task,
    update_submission_status,
)
from database.repo_users import get_user
from services.notifier import safe_send
from utils import texts
from utils.timez import TZ, from_db_str, humanize, now_tz

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=TZ)


def _job_id(prefix: str, task_id: int) -> str:
    return f"{prefix}_{task_id}"


async def _send_reminder(task_id: int, reminder_type: str, text_template: str) -> None:
    task = await get_task(task_id)
    if task is None or task["status"] != "active":
        return
    pending = await list_pending_submissions_for_task(task_id)
    for sub in pending:
        if await has_reminder_been_sent(task_id, sub["user_id"], reminder_type):
            continue
        text = text_template.format(title=task["title"], deadline=humanize(task["deadline"]))
        delivered = await safe_send(sub["user_id"], text)
        if delivered:
            await log_reminder(task_id, sub["user_id"], reminder_type)


async def _reminder_24h(task_id: int) -> None:
    await _send_reminder(task_id, "24h", texts.REMINDER_24H)


async def _reminder_3h(task_id: int) -> None:
    await _send_reminder(task_id, "3h", texts.REMINDER_3H)


async def _overdue_escalation(task_id: int) -> None:
    task = await get_task(task_id)
    if task is None or task["status"] != "active":
        return
    pending = await list_pending_submissions_for_task(task_id)
    if pending:
        names = "\n".join(f"• {p['full_name']}" for p in pending)
        mentor = await get_user(task["created_by"])
        if mentor:
            await safe_send(
                mentor["telegram_id"],
                texts.OVERDUE_MENTOR_ALERT.format(title=task["title"], names=names),
            )
        for sub in pending:
            await update_submission_status(sub["id"], "bajarmadi")
            await safe_send(sub["user_id"], texts.TASK_OVERDUE_PARTNER.format(title=task["title"]))
    await close_task(task_id, status="closed")


def schedule_task_reminders_sync(task_id: int, deadline: datetime) -> None:
    t_24h = deadline - timedelta(hours=24)
    t_3h = deadline - timedelta(hours=3)
    now = now_tz()

    if t_24h > now:
        scheduler.add_job(
            _reminder_24h, trigger=DateTrigger(run_date=t_24h, timezone=TZ),
            args=[task_id], id=_job_id("rem24", task_id), replace_existing=True,
        )
    if t_3h > now:
        scheduler.add_job(
            _reminder_3h, trigger=DateTrigger(run_date=t_3h, timezone=TZ),
            args=[task_id], id=_job_id("rem3", task_id), replace_existing=True,
        )
    scheduler.add_job(
        _overdue_escalation, trigger=DateTrigger(run_date=deadline, timezone=TZ),
        args=[task_id], id=_job_id("overdue", task_id), replace_existing=True,
    )


async def schedule_task_reminders(task_id: int, deadline: datetime) -> None:
    schedule_task_reminders_sync(task_id, deadline)


async def reschedule_task_reminders(task_id: int, new_deadline: datetime) -> None:
    for prefix in ("rem24", "rem3", "overdue"):
        job_id = _job_id(prefix, task_id)
        existing = scheduler.get_job(job_id)
        if existing:
            existing.remove()
    schedule_task_reminders_sync(task_id, new_deadline)


async def _proactive_checkin() -> None:
    """Send the 3-day check-in as ONE message per user listing all their
    pending tasks, instead of one message per pending task — otherwise a
    partner with 3 active tasks gets 3 back-to-back pings at 19:00.

    A single-task reminder still gets its own status buttons directly (no
    ambiguity). A multi-task summary intentionally carries no per-task action
    button — instead it links to /holat, where each task is listed with its
    own unambiguous status controls.
    """
    from keyboards.inline import task_status_kb, view_my_tasks_kb

    tasks = await list_all_active_tasks()
    pending_by_user: dict[int, list] = {}
    for task in tasks:
        pending = await list_pending_submissions_for_task(task["id"])
        for sub in pending:
            pending_by_user.setdefault(sub["user_id"], []).append((task, sub))

    for user_id, user_items in pending_by_user.items():
        if len(user_items) == 1:
            t, sub = user_items[0]
            text = texts.CHECKIN_3DAY.format(title=t["title"], deadline=humanize(t["deadline"]))
            await safe_send(user_id, text, reply_markup=task_status_kb(sub["id"]))
        else:
            lines = [texts.CHECKIN_3DAY_MULTI_HEADER.format(count=len(user_items))]
            for i, (t, _sub) in enumerate(user_items, start=1):
                lines.append(
                    texts.CHECKIN_3DAY_MULTI_ROW.format(index=i, title=t["title"], deadline=humanize(t["deadline"]))
                )
            text = "\n".join(lines)
            await safe_send(user_id, text, reply_markup=view_my_tasks_kb())


async def _monthly_settlement() -> None:
    from services.excel_export import build_monthly_report
    from database.repo_users import list_all_users
    from database.repo_tasks import list_active_tasks_for_partner
    from config import config as cfg

    path = await build_monthly_report()
    month_label = now_tz().strftime("%Y-%m")

    for admin_id in cfg.admin_ids:
        await safe_send(admin_id, texts.MONTHLY_REPORT_CAPTION.format(month=month_label))
        try:
            await get_bot_and_send_document(admin_id, path)
        except Exception:
            logger.exception("Failed to send monthly report to admin %s", admin_id)

    users = await list_all_users()
    for user in users:
        p_tasks = await list_active_tasks_for_partner(user["telegram_id"])
        # Note: this reflects currently-open tasks; closed-task history uses submissions/task status in DB.
        done = sum(1 for t in p_tasks if t["my_status"] == "bajardi")
        failed = sum(1 for t in p_tasks if t["my_status"] == "bajarmadi")
        pending = sum(1 for t in p_tasks if t["my_status"] in ("kutilmoqda", "jarayonda"))
        total = done + failed
        pct = (done / total * 100) if total else 0
        await safe_send(
            user["telegram_id"],
            texts.MONTHLY_SUMMARY_CARD.format(month=month_label, done=done, failed=failed, pending=pending, pct=pct),
        )


# ---------------------------------------------------------------------------
# Zoom session reminders (24h/3h/2h/1h) + post-session "did it happen?" check
# ---------------------------------------------------------------------------

def _zoom_job_id(prefix: str, session_id: int) -> str:
    return f"zoom_{prefix}_{session_id}"


async def _zoom_reminder(session_id: int, label: str) -> None:
    from database.repo_zoom import get_zoom_session
    from database.repo_cells import list_cell_partners

    session = await get_zoom_session(session_id)
    if session is None or session["status"] != "scheduled":
        return
    partners = await list_cell_partners(session["cell_id"])
    for p in partners:
        await safe_send(p["telegram_id"], f"⏰ Eslatma: Zoom dars {label} boshlanadi ({session['session_at']}).")


async def _zoom_reminder_24h(session_id: int) -> None:
    await _zoom_reminder(session_id, "24 soatdan so'ng")


async def _zoom_reminder_3h(session_id: int) -> None:
    await _zoom_reminder(session_id, "3 soatdan so'ng")


async def _zoom_reminder_2h(session_id: int) -> None:
    await _zoom_reminder(session_id, "2 soatdan so'ng")


async def _zoom_reminder_1h(session_id: int) -> None:
    await _zoom_reminder(session_id, "1 soatdan so'ng")


async def _zoom_post_check(session_id: int) -> None:
    from database.repo_zoom import get_zoom_session, ensure_confirmation_rows, set_zoom_session_status
    from database.repo_cells import list_cell_partners
    from keyboards.dynamic_menu import zoom_post_check_kb

    session = await get_zoom_session(session_id)
    if session is None or session["status"] != "scheduled":
        return
    partners = await list_cell_partners(session["cell_id"])
    partner_ids = [p["telegram_id"] for p in partners]
    await ensure_confirmation_rows(session_id, partner_ids)
    for pid in partner_ids:
        await safe_send(
            pid,
            f"🎥 Bugungi Zoom dars ({session['session_at']}) o'tdimi?",
            reply_markup=zoom_post_check_kb(session_id),
        )
    await set_zoom_session_status(session_id, "done")


def schedule_zoom_reminders_sync(session_id: int, cell_id: int, session_at: datetime) -> None:
    now = now_tz()
    offsets = [
        ("24h", timedelta(hours=24), _zoom_reminder_24h),
        ("3h", timedelta(hours=3), _zoom_reminder_3h),
        ("2h", timedelta(hours=2), _zoom_reminder_2h),
        ("1h", timedelta(hours=1), _zoom_reminder_1h),
    ]
    for prefix, delta, func in offsets:
        job_id = _zoom_job_id(prefix, session_id)
        existing = scheduler.get_job(job_id)
        if existing:
            existing.remove()
        run_at = session_at - delta
        if run_at > now:
            scheduler.add_job(
                func, trigger=DateTrigger(run_date=run_at, timezone=TZ),
                args=[session_id], id=job_id, replace_existing=True,
            )

    post_job_id = _zoom_job_id("postcheck", session_id)
    existing = scheduler.get_job(post_job_id)
    if existing:
        existing.remove()
    post_check_at = session_at + timedelta(hours=1)
    if post_check_at > now:
        scheduler.add_job(
            _zoom_post_check, trigger=DateTrigger(run_date=post_check_at, timezone=TZ),
            args=[session_id], id=post_job_id, replace_existing=True,
        )


async def unschedule_zoom_reminders(session_id: int) -> None:
    for prefix in ("24h", "3h", "2h", "1h", "postcheck"):
        job_id = _zoom_job_id(prefix, session_id)
        existing = scheduler.get_job(job_id)
        if existing:
            existing.remove()


# ---------------------------------------------------------------------------
# Weekly plan: every 2-3 days auto "bajardingizmi?" nudge for pending days
# ---------------------------------------------------------------------------

async def _weekly_plan_checkin_nudge() -> None:
    from database.repo_weekly_plan import list_pending_checkins_needing_reminder, mark_reminder_sent
    from keyboards.dynamic_menu import weekly_plan_day_checkin_kb

    rows = await list_pending_checkins_needing_reminder()
    for row in rows:
        delivered = await safe_send(
            row["user_id"],
            f"🗓 Eslatma: {row['day_number']}-kun vazifasini bajardingizmi?\n{row['content']}",
            reply_markup=weekly_plan_day_checkin_kb(row["plan_day_id"]),
        )
        if delivered:
            await mark_reminder_sent(row["plan_day_id"], row["user_id"])


# ---------------------------------------------------------------------------
# Weekly plan: daily auto-distribution of days 2-7 to partners
# ---------------------------------------------------------------------------

async def _weekly_plan_daily_distribution() -> None:
    from database.repo_cells import list_cell_partners
    from database.repo_weekly_plan import list_plan_days_pending_distribution, mark_plan_day_distributed
    from keyboards.dynamic_menu import weekly_plan_day_checkin_kb

    days = await list_plan_days_pending_distribution()
    for day in days:
        partners = await list_cell_partners(day["cell_id"])
        for p in partners:
            await safe_send(
                p["telegram_id"],
                f"🗓 <b>{day['day_number']}-kun vazifasi:</b>\n{day['content']}",
                reply_markup=weekly_plan_day_checkin_kb(day["id"]),
            )
        await mark_plan_day_distributed(day["id"])


async def get_bot_and_send_document(chat_id: int, path: str) -> None:
    from aiogram.types import FSInputFile
    from services.notifier import get_bot

    await get_bot().send_document(chat_id, FSInputFile(path))


def start_scheduler() -> None:
    scheduler.add_job(
        _proactive_checkin,
        trigger=CronTrigger(day="*/3", hour=19, minute=0, timezone=TZ),
        id="proactive_checkin",
        replace_existing=True,
    )
    scheduler.add_job(
        _monthly_settlement,
        trigger=CronTrigger(day=1, hour=8, minute=0, timezone=TZ),
        id="monthly_settlement",
        replace_existing=True,
    )
    scheduler.add_job(
        _weekly_plan_checkin_nudge,
        trigger=CronTrigger(day="*/2", hour=19, minute=30, timezone=TZ),
        id="weekly_plan_checkin_nudge",
        replace_existing=True,
    )
    scheduler.add_job(
        _weekly_plan_daily_distribution,
        trigger=CronTrigger(hour=8, minute=0, timezone=TZ),
        id="weekly_plan_daily_distribution",
        replace_existing=True,
    )
    scheduler.start()


async def reschedule_all_active_tasks_on_startup() -> None:
    """Re-register reminder/overdue jobs for all active tasks after a restart."""
    tasks = await list_all_active_tasks()
    for task in tasks:
        deadline = from_db_str(task["deadline"])
        if deadline <= now_tz():
            await _overdue_escalation(task["id"])
        else:
            schedule_task_reminders_sync(task["id"], deadline)

    from database.repo_zoom import list_due_scheduled_sessions
    from database.db import get_conn

    conn = get_conn()
    cur = await conn.execute("SELECT * FROM zoom_sessions WHERE status = 'scheduled'")
    sessions = await cur.fetchall()
    for s in sessions:
        session_at = datetime.strptime(s["session_at"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        if session_at + timedelta(hours=1) <= now_tz():
            await _zoom_post_check(s["id"])
        else:
            schedule_zoom_reminders_sync(s["id"], s["cell_id"], session_at)
