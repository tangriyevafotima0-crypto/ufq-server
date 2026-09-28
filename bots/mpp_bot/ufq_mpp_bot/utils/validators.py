from __future__ import annotations

import re
from datetime import datetime

from utils.timez import now_tz, parse_deadline

INVITE_CODE_RE = re.compile(r"^\d{6}$")
DEADLINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def is_valid_invite_code(code: str) -> bool:
    return bool(INVITE_CODE_RE.match(code.strip()))


def validate_deadline_input(raw: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message). error_message is empty if valid."""
    raw = raw.strip()
    if not DEADLINE_RE.match(raw):
        return False, "Format noto'g'ri. Iltimos, quyidagicha kiriting: YYYY-MM-DD HH:MM (masalan: 2026-09-15 18:00)"
    try:
        dt = parse_deadline(raw)
    except ValueError:
        return False, "Sana yoki vaqt noto'g'ri kiritildi. Qayta urinib ko'ring."
    if dt <= now_tz():
        return False, "Muddat kelajakda bo'lishi kerak. Qayta urinib ko'ring."
    return True, ""


def validate_score_input(raw: str, direction_name: str | None = None) -> tuple[bool, str, float]:
    """Validate a mock score, applying a direction-specific sane range when the
    direction name matches a known test type (IELTS: 0-9 in 0.5 steps, SAT:
    400-1600). Falls back to a generic 0-100 range for unrecognized directions
    so custom/local tracks aren't blocked.
    """
    raw = raw.strip().replace(",", ".")
    try:
        score = float(raw)
    except ValueError:
        return False, "Ball raqam ko'rinishida bo'lishi kerak (masalan: 6.5).", 0.0

    name = (direction_name or "").strip().upper()
    if name == "IELTS":
        if not (0.0 <= score <= 9.0):
            return False, "IELTS bali 0.0 dan 9.0 gacha oralig'ida bo'lishi kerak.", 0.0
        if round(score * 2) != score * 2:
            return False, "IELTS bali 0.5 qadam bilan bo'lishi kerak (masalan: 6.5, 7.0).", 0.0
        return True, "", score
    if "SAT" in name and ("MATH" in name or "READING" in name or "WRITING" in name):
        # A single SAT section (Math, or Reading & Writing) is scored 200-800,
        # not the 400-1600 composite scale — distinct from a general "SAT"
        # direction that tracks the combined score.
        if not (200 <= score <= 800):
            return False, "SAT bo'lim bali 200 dan 800 gacha oralig'ida bo'lishi kerak.", 0.0
        if score != int(score) or int(score) % 10 != 0:
            return False, "SAT bo'lim bali 10 ball qadami bilan butun son bo'lishi kerak (masalan: 650).", 0.0
        return True, "", score
    if name == "SAT":
        if not (400 <= score <= 1600):
            return False, "SAT bali 400 dan 1600 gacha oralig'ida bo'lishi kerak.", 0.0
        if score != int(score) or int(score) % 10 != 0:
            return False, "SAT bali 10 ball qadami bilan butun son bo'lishi kerak (masalan: 1200).", 0.0
        return True, "", score

    if score < 0 or score > 100:
        return False, "Ball 0 dan 100 gacha oralig'ida bo'lishi kerak.", 0.0
    return True, "", score


def validate_date_input(raw: str) -> tuple[bool, str]:
    raw = raw.strip()
    try:
        datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return False, "Sana formati noto'g'ri. Masalan: 2026-09-10"
    return True, ""


def normalize_username(raw: str) -> str:
    return raw.strip().lstrip("@")


def is_telegram_id(raw: str) -> bool:
    return raw.strip().isdigit()
