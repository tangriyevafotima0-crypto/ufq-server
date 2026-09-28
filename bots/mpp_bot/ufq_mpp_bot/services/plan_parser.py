"""
services/plan_parser.py
------------------------
Turns a mentor-supplied weekly plan (raw text extracted from a .docx/.txt
file, or typed directly) into 7 day-by-day entries.

Two-stage strategy (per QOLGAN_ISHLAR.md):
  1. Pattern match: look for explicit "1-kun / Day 1 / Kun 1" style markers.
     If all 7 days are found this way, use them directly -- no AI call.
  2. AI fallback: if the pattern doesn't match, hand the raw text to Claude
     (via the Anthropic API) with an instruction to reshape it into the
     canonical 7-line pattern, then parse that output with the same
     pattern matcher.

If no ANTHROPIC_API_KEY is configured (or the call fails), falls back to a
naive split so mentors are never fully blocked -- the mentor can always
correct results afterwards via the "planni tahrirlash" flow.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("ufq_mpp_bot")

_DAY_LINE_RE = re.compile(
    r"^\s*(?:(\d)[-\s]*kun|day\s*(\d)|kun\s*(\d))\s*[:.\-–)]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class ParsedPlan:
    days: dict[int, str]  # day_number (1-7) -> content
    method: str  # "pattern" | "ai" | "fallback_split"
    complete: bool  # True if all 7 days were found


def _try_pattern_match(text: str) -> dict[int, str]:
    days: dict[int, str] = {}
    for match in _DAY_LINE_RE.finditer(text):
        day_num = next(g for g in match.groups()[:3] if g is not None)
        day_num = int(day_num)
        content = match.group(4).strip()
        if 1 <= day_num <= 7 and content:
            days[day_num] = content
    return days


def _fallback_split(text: str) -> dict[int, str]:
    """No recognizable pattern and no AI available: split non-empty lines
    across 7 days as evenly as possible so nothing is silently dropped."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {}
    days: dict[int, str] = {}
    if len(lines) <= 7:
        for i, line in enumerate(lines, start=1):
            days[i] = line
    else:
        chunk = len(lines) / 7
        for day in range(1, 8):
            start = int((day - 1) * chunk)
            end = int(day * chunk) if day < 7 else len(lines)
            days[day] = "\n".join(lines[start:end]) or "—"
    return days


_AI_SYSTEM_PROMPT = (
    "You reformat a mentor's weekly study plan into EXACTLY 7 lines, one per "
    "day, in this exact pattern and nothing else:\n"
    "1-kun: <task text>\n2-kun: <task text>\n...\n7-kun: <task text>\n"
    "Keep the original language and content of each task, just organize it "
    "into 7 days. If fewer than 7 distinct tasks exist, distribute or split "
    "reasonably so all 7 days are filled. Output ONLY the 7 lines, nothing else."
)


async def _try_ai_reformat(text: str) -> str | None:
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_AI_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:8000]}],
        )
        out_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "\n".join(out_parts).strip() or None
    except Exception:
        logger.exception("AI plan reformat failed; using fallback split")
        return None


async def parse_weekly_plan(text: str) -> ParsedPlan:
    text = text.strip()
    days = _try_pattern_match(text)
    if len(days) >= 7:
        return ParsedPlan(days=days, method="pattern", complete=True)

    ai_output = await _try_ai_reformat(text)
    if ai_output:
        ai_days = _try_pattern_match(ai_output)
        if ai_days:
            return ParsedPlan(days=ai_days, method="ai", complete=len(ai_days) >= 7)

    if days:
        return ParsedPlan(days=days, method="pattern", complete=False)

    return ParsedPlan(days=_fallback_split(text), method="fallback_split", complete=False)
