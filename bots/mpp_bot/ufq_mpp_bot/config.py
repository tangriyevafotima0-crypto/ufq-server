from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    out: set[int] = set()
    for chunk in raw.replace(" ", "").split(","):
        if chunk:
            out.add(int(chunk))
    return out


@dataclass(frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: os.environ["BOT_TOKEN"])
    admin_ids: set[int] = field(default_factory=lambda: _parse_admin_ids(os.getenv("ADMIN_IDS")))
    timezone: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Asia/Tashkent"))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "database/ufq_mpp.db"))
    schema_path: str = field(default_factory=lambda: os.getenv("SCHEMA_PATH", "database/schema.sql"))
    export_dir: str = field(default_factory=lambda: os.getenv("EXPORT_DIR", "exports"))


config = Config()
