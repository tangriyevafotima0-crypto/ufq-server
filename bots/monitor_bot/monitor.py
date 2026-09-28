"""
monitor.py — Kuzatuvchi yadro
Kanallarni polling qilib, yangi postlardan mos imkoniyatlarni topadi
va DARHOL (digest kutmasdan) adminga va tasdiqlangan guruh(lar)ga yuboradi.

parser va matcher modullaridan foydalanadi. Background task sifatida
ishga tushadi.
"""

import asyncio
import hashlib
import logging
from datetime import date, datetime
from typing import Callable, Optional

from parser import parse_post
from matcher import Profile, evaluate

# FloodWait'ni alohida ushlash uchun (telethon bo'lmasa — test rejimi)
try:
    from telethon.errors import FloodWaitError
except Exception:  # pragma: no cover
    class FloodWaitError(Exception):
        seconds = 0

# Bitta FloodWait uchun maksimal kutish (soniya) — undan uzun bo'lsa
# kanalni o'tkazib yuboramiz (butun tsikl qotib qolmasligi uchun).
_MAX_FLOOD_WAIT = 300

# Bir tekshiruv siklida bitta kanaldan olinadigan yangi xabarlar chegarasi.
# Cheksiz bo'lsa, uzoq vaqt to'xtab qolgan monitor RAM/vaqtni portlatishi mumkin.
_MAX_NEW_PER_CHANNEL = 200

log = logging.getLogger("monitor")


async def _handle_flood(e, label: str) -> None:
    """FloodWaitError'ni hurmat qiladi: Telegram so'ragan vaqtni kutadi."""
    wait = int(getattr(e, "seconds", 0) or 0)
    wait = min(wait, _MAX_FLOOD_WAIT)
    log.warning(f"{label}: FloodWait — {wait}s kutilmoqda (Telegram limiti)")
    await asyncio.sleep(wait + 1)


def _opp_hash(opp) -> str:
    """Imkoniyat uchun yagona hash (takror oldini olish)."""
    key = f"{opp.title[:60].lower().strip()}|{opp.deadline}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:16]


def _profile_from_dict(d: dict) -> Profile:
    return Profile(
        age=d.get("age", 16),
        grade=d.get("grade"),
        ielts=d.get("ielts"),
        knows_english=d.get("knows_english", True),
        is_student=d.get("is_student", False),
        is_pupil=d.get("is_pupil", True),
        interests=d.get("interests", []),
        only_free=d.get("only_free", True),
    )


def _msg_to_text(msg) -> str:
    """Telethon xabaridan to'liq matnni oladi."""
    return (msg.text or msg.message or "").strip()


def format_opportunity(opp, channel_name: str) -> str:
    """Bitta imkoniyatni Telegram xabari uchun formatlaydi."""
    def _md_safe(text: str) -> str:
        if not text:
            return ""
        for ch in ["*", "_", "`", "[", "]"]:
            text = text.replace(ch, "")
        return text

    title = _md_safe(opp.title[:120])
    lines = [f"🎯 **{title}**"]

    if opp.deadline:
        days_left = (opp.deadline - date.today()).days
        if days_left <= 3:
            lines.append(f"⏰ **{days_left} kun qoldi!** ({opp.deadline})")
        elif days_left <= 7:
            lines.append(f"📅 {days_left} kun qoldi ({opp.deadline})")
        else:
            lines.append(f"📅 {opp.deadline} ({days_left} kun)")

    if opp.is_free:
        lines.append("💰 Bepul / Grant")
    if opp.fields:
        lines.append(f"🏷 {_md_safe(', '.join(opp.fields))}")
    if opp.match_reasons:
        reasons_clean = _md_safe(" · ".join(r.lstrip("✅✓ ") for r in opp.match_reasons[:3]))
        lines.append("✅ " + reasons_clean)
    lines.append(f"📎 {_md_safe(channel_name)}")
    if opp.link:
        lines.append(f"🔗 {opp.link}")

    return "\n".join(lines)


class ChannelMonitor:
    """Kanallarni kuzatuvchi va topilgan imkoniyatlarni darhol yetkazuvchi."""

    def __init__(self, user_client, state, resolve_target_fn: Callable):
        self.user = user_client
        self.state = state
        self.resolve_target = resolve_target_fn
        self._task: Optional[asyncio.Task] = None
        # Bir vaqtda bitta skan: background tsikl va /scan_now
        # bir-birini bosib ketmasligi uchun (race + qo'shaloq xabar fix).
        self._scan_lock = asyncio.Lock()

    async def poll_once(self, on_match: Callable) -> int:
        """
        Barcha kanallarni bir marta tekshiradi.
        Har topilgan mos imkoniyat uchun DARHOL on_match(opp, channel_name)
        chaqiriladi (async funksiya bo'lishi kerak).
        Qaytaradi: topilgan yangi imkoniyatlar soni.
        """
        async with self._scan_lock:
            return await self._poll_once_locked(on_match)

    async def _poll_once_locked(self, on_match: Callable) -> int:
        profile = _profile_from_dict(self.state.profile)
        min_score = self.state.settings.get("min_score", 40)
        today = date.today()
        found_count = 0

        watched = dict(self.state.watched)   # nusxa — iteratsiya paytida o'zgarmasin

        for cid_str, channel_name in watched.items():
            try:
                cid = int(cid_str)
                entity = await self.resolve_target(self.user, cid_str)
                if entity is None:
                    log.warning(f"Monitor: kanal topilmadi {cid_str} ({channel_name})")
                    continue

                last_seen = self.state.get_last_seen(cid)

                # Yangi qo'shilgan kanal (baseline o'rnatilmagan):
                # eski postlarni qayta ishlamaymiz — faqat oxirgi ID ni belgilaymiz.
                if last_seen == 0:
                    async for msg in self.user.iter_messages(entity, limit=1):
                        self.state.set_last_seen(cid, msg.id)
                        log.info(f"Baseline (poll): {channel_name} #{msg.id}")
                        break
                    await asyncio.sleep(1)
                    continue

                new_max_id = last_seen

                # Yangi xabarlarni ESKIDAN-YANGIGA olamiz (reverse=True).
                # Bu tartib muhim: agar ko'p post yig'ilgan bo'lsa
                # (bot to'xtab qolgan), birortasi ham o'tkazib yuborilmaydi.
                # min_id eksklyuziv — faqat last_seen dan keyingilar.
                new_messages = []
                async for msg in self.user.iter_messages(
                    entity, min_id=last_seen, reverse=True,
                    limit=_MAX_NEW_PER_CHANNEL,
                ):
                    new_messages.append(msg)
                    if msg.id > new_max_id:
                        new_max_id = msg.id

                # Har bir yangi postni tahlil qilamiz
                for msg in new_messages:
                    text = _msg_to_text(msg)
                    if len(text) < 40:
                        continue

                    post_date = msg.date.date() if msg.date else today
                    opp = parse_post(text, post_date, channel_name)
                    evaluate(opp, profile, today)

                    # Mos kelganmi va yetarli ballmi?
                    if opp.score < min_score or opp.reject_reasons:
                        continue

                    # Takror yuborilganmi?
                    h = _opp_hash(opp)
                    if self.state.is_sent(h):
                        continue

                    self.state.mark_sent(h)
                    found_count += 1
                    log.info(f"Yangi imkoniyat [{opp.score}]: {opp.title[:50]}")

                    try:
                        await on_match(opp, channel_name)
                    except Exception:
                        log.exception("on_match callback xatosi")

                # Oxirgi ko'rilgan ID ni yangilaymiz.
                # DIQQAT: yangilanish on_match dan KEYIN — agar yuborish paytida
                # jarayon to'xtab qolsa, keyingi tekshiruvda post qayta ko'riladi
                # (o'tkazib yuborilgandan ko'ra, kamdan-kam holatda takror yaxshiroq).
                if new_max_id > last_seen:
                    self.state.set_last_seen(cid, new_max_id)
                # last_seen har kanaldan keyin darhol diskka yozamiz — agar
                # jarayon keyingi kanalda yiqilsa, bu kanal progressi yo'qolmaydi.
                self.state.save()

                # Kanallar orasida kutamiz (FloodWait oldini olish)
                await asyncio.sleep(2)

            except FloodWaitError as e:
                await _handle_flood(e, f"Monitor {channel_name}")
            except Exception as e:
                log.warning(f"Monitor xatosi {channel_name}: {e}")
                await asyncio.sleep(2)

        # Holatni saqlaymiz
        self.state.record_check(found_count, datetime.now().isoformat())
        self.state.save()

        return found_count

    async def init_baseline(self):
        """
        Monitor yoqilganda — har kanalning hozirgi oxirgi post ID sini
        last_seen sifatida belgilaydi. Shunda faqat BUNDAN KEYINGI
        postlar tekshiriladi (eski postlar yuborilmaydi).
        """
        watched = dict(self.state.watched)
        for cid_str, channel_name in watched.items():
            try:
                cid = int(cid_str)
                if self.state.get_last_seen(cid) > 0:
                    continue   # allaqachon belgilangan
                entity = await self.resolve_target(self.user, cid_str)
                if entity is None:
                    continue
                async for msg in self.user.iter_messages(entity, limit=1):
                    self.state.set_last_seen(cid, msg.id)
                    log.info(f"Baseline {channel_name}: oxirgi post #{msg.id}")
                    break
                await asyncio.sleep(1)
            except Exception as e:
                log.warning(f"Baseline xatosi {channel_name}: {e}")
        self.state.save()

    async def run_forever(self, on_match: Callable):
        """
        Cheksiz monitoring tsikli.
        Har check_interval da kanallarni tekshiradi va topilgan har bir
        mos postni darhol on_match orqali yuboradi.
        """
        log.info("Monitor tsikli boshlandi")
        # Yoqilganda baseline o'rnatamiz
        await self.init_baseline()

        while self.state.enabled:
            try:
                interval = self.state.settings.get("check_interval", 600)

                found = await self.poll_once(on_match)
                if found:
                    log.info(f"Tekshiruv: {found} yangi imkoniyat topildi va yuborildi")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                log.info("Monitor tsikli to'xtatildi")
                break
            except Exception as e:
                log.exception(f"Monitor tsikl xatosi: {e}")
                await asyncio.sleep(60)   # xatodan keyin 1 daqiqa kutamiz

    def start(self, on_match: Callable):
        """Background task sifatida ishga tushiradi."""
        if self._task and not self._task.done():
            return False
        self._task = asyncio.create_task(self.run_forever(on_match))
        return True

    def stop(self):
        """Tsiklni to'xtatadi."""
        if self._task and not self._task.done():
            self._task.cancel()
