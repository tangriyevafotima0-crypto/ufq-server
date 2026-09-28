from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from config import config

TZ = ZoneInfo(config.timezone)


def now_tz() -> datetime:
    """Current time in the configured timezone (Asia/Tashkent), tz-aware."""
    return datetime.now(TZ)


def now_str() -> str:
    return now_tz().strftime("%Y-%m-%d %H:%M:%S")


def parse_deadline(raw: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM' user input into a tz-aware Asia/Tashkent datetime.

    Raises ValueError on malformed input.
    """
    naive = datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=TZ)


def to_db_str(dt: datetime) -> str:
    """Format a tz-aware datetime as naive local string for SQLite storage."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(TZ).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def from_db_str(raw: str) -> datetime:
    """Parse a naive DB timestamp string back into tz-aware Asia/Tashkent datetime."""
    naive = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    return naive.replace(tzinfo=TZ)


def humanize(raw: str) -> str:
    dt = from_db_str(raw)
    return dt.strftime("%d.%m.%Y %H:%M")


UZ_MONTH_NAMES = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr",
]


def uz_month_name(dt: datetime) -> str:
    return UZ_MONTH_NAMES[dt.month - 1]
