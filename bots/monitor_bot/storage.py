"""
storage.py — Bot holatini saqlash
JSON fayl orqali: kuzatilayotgan kanallar, ulangan guruh(lar),
oxirgi ko'rilgan post, profil, yuborilgan imkoniyatlar, sozlamalar.

Guruh oqimi:
  - Admin /group_add bilan guruh ID sini kiritadi (pending holatga o'tadi).
  - Admin /group_confirm bilan tasdiqlaydi (bot o'sha guruhda admin
    bo'lishi tekshiriladi — bot.py da).
  - Faqat tasdiqlangan guruhga post yuboriladi.
"""

import json
import threading
from pathlib import Path
from typing import Any, Optional


class BotState:
    """Bot holati — thread-safe JSON saqlash."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._data = self._load()

    def _default(self) -> dict:
        return {
            "enabled": False,                # monitor yoqilganmi
            "watched_channels": {},          # {"channel_id": "nomi"}
            "last_seen": {},                 # {"channel_id": oxirgi_msg_id}
            "groups": {},                    # {"chat_id": {"title":, "status": "pending"|"confirmed"}}
            "profile": {
                "age": 16,
                "grade": 11,
                "ielts": 6.0,
                "knows_english": True,
                "is_student": False,
                "is_pupil": True,
                "interests": ["IT", "Biznes", "Debat", "Til", "Liderlik"],
                "only_free": True,
            },
            "settings": {
                "check_interval": 600,       # 10 daqiqa
                "min_score": 40,             # faqat kuchli mos
            },
            "sent_hashes": [],               # yuborilgan imkoniyatlar (takror oldini)
            "stats": {
                "total_checks": 0,
                "total_found": 0,
                "last_check": "",
            },
        }

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Yetishmayotgan kalitlarni to'ldiramiz (migratsiya)
                default = self._default()
                for key, val in default.items():
                    if key not in data:
                        data[key] = val
                    elif isinstance(val, dict):
                        for subkey, subval in val.items():
                            if subkey not in data[key]:
                                data[key][subkey] = subval
                return data
            except Exception:
                pass
        return self._default()

    def save(self):
        """Holatni diskka yozadi (atomik)."""
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            tmp.replace(self.path)

    # ── Yoqilgan/o'chirilgan ─────────────────────────

    @property
    def enabled(self) -> bool:
        return self._data["enabled"]

    @enabled.setter
    def enabled(self, val: bool):
        self._data["enabled"] = val
        self.save()

    # ── Kuzatilayotgan kanallar ──────────────────────

    @property
    def watched(self) -> dict:
        return self._data["watched_channels"]

    def add_channel(self, channel_id: int, name: str):
        self._data["watched_channels"][str(channel_id)] = name
        self.save()

    def remove_channel(self, channel_id: int) -> bool:
        cid = str(channel_id)
        if cid in self._data["watched_channels"]:
            del self._data["watched_channels"][cid]
            self._data["last_seen"].pop(cid, None)
            self.save()
            return True
        return False

    def get_last_seen(self, channel_id: int) -> int:
        return self._data["last_seen"].get(str(channel_id), 0)

    def set_last_seen(self, channel_id: int, msg_id: int):
        self._data["last_seen"][str(channel_id)] = msg_id
        # save() chaqirmaymiz — poll oxirida bir marta saqlanadi

    # ── Guruhlar ──────────────────────────────────────

    @property
    def groups(self) -> dict:
        return self._data["groups"]

    def add_pending_group(self, chat_id: int, title: str):
        self._data["groups"][str(chat_id)] = {"title": title, "status": "pending"}
        self.save()

    def confirm_group(self, chat_id: int) -> bool:
        g = self._data["groups"].get(str(chat_id))
        if not g:
            return False
        g["status"] = "confirmed"
        self.save()
        return True

    def remove_group(self, chat_id: int) -> bool:
        cid = str(chat_id)
        if cid in self._data["groups"]:
            del self._data["groups"][cid]
            self.save()
            return True
        return False

    def get_group(self, chat_id: int) -> Optional[dict]:
        return self._data["groups"].get(str(chat_id))

    def confirmed_group_ids(self) -> list:
        return [int(cid) for cid, g in self._data["groups"].items()
                if g.get("status") == "confirmed"]

    def pending_group_ids(self) -> list:
        return [int(cid) for cid, g in self._data["groups"].items()
                if g.get("status") == "pending"]

    # ── Profil ────────────────────────────────────────

    @property
    def profile(self) -> dict:
        return self._data["profile"]

    def update_profile(self, key: str, value: Any):
        self._data["profile"][key] = value
        self.save()

    # ── Sozlamalar ────────────────────────────────────

    @property
    def settings(self) -> dict:
        return self._data["settings"]

    def update_setting(self, key: str, value: Any):
        self._data["settings"][key] = value
        self.save()

    # ── Takror oldini olish ──────────────────────────

    def is_sent(self, opp_hash: str) -> bool:
        return opp_hash in self._data["sent_hashes"]

    def mark_sent(self, opp_hash: str):
        self._data["sent_hashes"].append(opp_hash)
        # Ro'yxat juda uzun bo'lmasligi uchun — oxirgi 5000 ta
        if len(self._data["sent_hashes"]) > 5000:
            self._data["sent_hashes"] = self._data["sent_hashes"][-5000:]

    # ── Statistika ───────────────────────────────────

    def record_check(self, found: int, when: str):
        self._data["stats"]["total_checks"] += 1
        self._data["stats"]["total_found"] += found
        self._data["stats"]["last_check"] = when

    @property
    def stats(self) -> dict:
        return self._data["stats"]
