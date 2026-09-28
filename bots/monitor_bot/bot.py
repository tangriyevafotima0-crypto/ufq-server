"""
Telegram Imkoniyat Monitor Bot
Faqat bitta vazifa: kuzatilayotgan kanallardagi postlarni o'qib,
profilga mos "imkoniyat"larni aniqlaydi va DARHOL:
  - botning egasiga (shaxsiy chatga), va
  - admin bir marta ro'yxatdan o'tkazib tasdiqlagan guruh(lar)ga
yuboradi.

Guruhga yuborish shartlari:
  1) Ega /group_add buyrug'i bilan guruhni ro'yxatga kiritadi (pending).
  2) Bot o'sha guruhda ADMIN bo'lishi kerak.
  3) Ega /group_confirm bilan tasdiqlaydi — shundan keyingina
     guruh xabar oladigan bo'ladi.
Tasdiqlanmagan yoki botga admin huquqi berilmagan guruhga HECH NARSA
yuborilmaydi.
"""

import asyncio
import functools
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, PeerChannel, PeerChat, PeerUser

from storage import BotState
from monitor import ChannelMonitor, format_opportunity

# ═══════════════════════════════════════════════════════
# KONFIGURATSIYA
# ═══════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        print(f"[FATAL] .env da '{key}' topilmadi yoki bo'sh!", file=sys.stderr)
        sys.exit(1)
    return val


def _validate_session(session: str) -> str:
    """
    Session string'ni faqat oddiy hafsalasizliklardan (bo'sh joy, tirnoq,
    qatorlar) tozalaydi. Telethon StringSession formati o'zi to'g'ri
    base64 kodlaydi va '=' padding kerak emas — shuning uchun bu yerda
    padding "tuzatish" URINISH QILINMAYDI: haqiqiy (to'g'ri) session
    deyarli har doim 4 ga bo'linmaydigan uzunlikka ega bo'ladi, va uni
    zo'rlab paddinglash boshqa (noto'g'ri) session ishlab chiqaradi —
    bu haqiqiy xatoni yashiradi va login muvaffaqiyatsiz tugaydi.
    Haqiqiy uzilish/yaroqsizlik `is_user_authorized()` orqali aniqlanadi.
    """
    session = session.strip().strip('"').strip("'")
    # Ba'zi editor/terminal joylashtirishlarida qatorlar orasiga
    # bo'sh joy yoki qator uzilishi tushib qolishi mumkin.
    session = "".join(session.split())
    return session


API_ID           = int(_require("API_ID"))
API_HASH         = _require("API_HASH")
BOT_TOKEN        = _require("BOT_TOKEN")
OWNER_ID         = int(_require("OWNER_ID"))
USER_SESSION_STR = _validate_session(_require("USER_SESSION_STR"))

STATE_PATH = BASE_DIR / "monitor_state.json"
LOG_FILE   = BASE_DIR / "monitor_bot.log"

# ═══════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════


def _setup_logging():
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    logging.getLogger("telethon").setLevel(logging.WARNING)


_setup_logging()
log = logging.getLogger("monitor_bot")

_shutdown_event = asyncio.Event()

VALID_INTERESTS = ["IT", "Til", "Fan", "Biznes", "Debat",
                    "Liderlik", "Madaniyat", "San'at"]


# ═══════════════════════════════════════════════════════
# YORDAMCHI: KANAL/GURUH TOPISH
# ═══════════════════════════════════════════════════════

def _client_cache(client) -> dict:
    cache = getattr(client, "_dialog_cache", None)
    if cache is None:
        cache = {}
        client._dialog_cache = cache
    return cache


async def _load_dialog_cache(client: TelegramClient) -> int:
    """Barcha dialoglarni yuklab keshga yozadi (ID orqali topish uchun)."""
    new_cache: dict = {}
    count = 0
    try:
        async for dialog in client.iter_dialogs():
            ent = dialog.entity
            eid = getattr(ent, "id", None)
            did = dialog.id
            if did is not None:
                new_cache[did] = ent
            if eid is not None and eid != did:
                new_cache[eid] = ent
            count += 1
        client._dialog_cache = new_cache
        log.info(f"Dialog kesh yuklandi: {count} ta dialog, {len(new_cache)} kalit")
    except FloodWaitError as e:
        log.warning(f"FloodWait dialog kesh yuklashda: {e.seconds}s")
    except Exception as e:
        log.warning(f"Dialog kesh yuklanmadi: {e}")
    return count


def _entity_name(entity) -> str:
    return getattr(entity, "title", None) or str(getattr(entity, "id", "?"))


async def resolve_target(client: TelegramClient, target: str):
    """
    Kanal/guruhni username, t.me link yoki ID bo'yicha topadi.
    Strategy chain: bir necha usul ketma-ket sinaladi.
    Hammasi muvaffaqiyatsiz bo'lsa — None.
    """
    target = target.strip()
    cache = _client_cache(client)

    if not target.lstrip("-").isdigit():
        try:
            ent = await client.get_entity(target)
            return ent
        except FloodWaitError:
            raise
        except Exception:
            pass
        try:
            inp = await client.get_input_entity(target)
            ent = await client.get_entity(inp)
            return ent
        except FloodWaitError:
            raise
        except Exception:
            pass
        return None

    raw = target.lstrip("-")
    t_int = int(target)
    t_abs = int(raw)

    if raw.startswith("100") and len(raw) > 10:
        raw_ch = int(raw[3:])
    else:
        raw_ch = t_abs

    def _from_cache():
        for key in (t_int, -t_abs, t_abs, raw_ch, -raw_ch):
            if key in cache:
                return cache[key]
        return None

    def _cache_entity(ent):
        cache[t_int] = ent
        eid = getattr(ent, "id", None)
        if eid:
            cache[eid] = ent

    hit = _from_cache()
    if hit:
        return hit

    for cand in (t_int, -t_abs, t_abs, raw_ch):
        try:
            ent = await client.get_entity(cand)
            _cache_entity(ent)
            return ent
        except FloodWaitError:
            raise
        except Exception:
            pass

    for cand in (t_int, raw_ch):
        try:
            inp = await client.get_input_entity(cand)
            ent = await client.get_entity(inp)
            _cache_entity(ent)
            return ent
        except FloodWaitError:
            raise
        except Exception:
            pass

    for pid in (raw_ch, t_abs):
        try:
            ent = await client.get_entity(PeerChannel(pid))
            _cache_entity(ent)
            return ent
        except FloodWaitError:
            raise
        except Exception:
            pass

    for pid in (raw_ch, t_abs):
        try:
            ent = await client.get_entity(PeerChat(pid))
            _cache_entity(ent)
            return ent
        except FloodWaitError:
            raise
        except Exception:
            pass

    try:
        ent = await client.get_entity(PeerUser(t_abs))
        _cache_entity(ent)
        return ent
    except FloodWaitError:
        raise
    except Exception:
        pass

    await _load_dialog_cache(client)
    cache = _client_cache(client)
    hit = _from_cache()
    if hit:
        return hit

    return None


# ═══════════════════════════════════════════════════════
# DECORATOR
# ═══════════════════════════════════════════════════════

def owner_only(handler):
    """Faqat bot egasi, faqat shaxsiy chatda."""
    @functools.wraps(handler)
    async def wrapper(event):
        if not event.is_private:
            return
        if event.sender_id != OWNER_ID:
            return
        await handler(event)
    return wrapper


def owner_in_group(handler):
    """Faqat bot egasi, faqat guruh/superguruh ichida (guruh buyruqlari uchun)."""
    @functools.wraps(handler)
    async def wrapper(event):
        if event.is_private:
            return
        if event.sender_id != OWNER_ID:
            return
        await handler(event)
    return wrapper


# ═══════════════════════════════════════════════════════
# BOT HANDLERLARI
# ═══════════════════════════════════════════════════════

def register_handlers(bot: TelegramClient, user: TelegramClient, state: BotState):

    # /group_add dan keyin /group_confirm kutilayotgan guruhlar allaqachon
    # state.groups ichida "pending" statusda saqlanadi (persistent — restartga chidamli).

    async def _check_bot_is_admin(chat_id: int) -> bool:
        """Bot (bot_client) shu guruhda admin ekanini tekshiradi."""
        try:
            me = await bot.get_me()
            perms = await bot.get_permissions(chat_id, me.id)
            return bool(perms.is_admin or perms.is_creator)
        except Exception as e:
            log.warning(f"Admin tekshiruvi xatosi ({chat_id}): {e}")
            return False

    # ── /start ──────────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/start$"))
    async def cmd_start(event):
        if not event.is_private:
            return
        if event.sender_id != OWNER_ID:
            await event.reply(
                "👋 Salom! Bu bot yopiq — faqat egasi uchun ishlaydi.\n"
                f"Sizning ID ingiz: `{event.sender_id}`"
            )
            return
        text = (
            "👋 **Imkoniyat Monitor Bot**\n\n"
            "**🎯 Kanal kuzatuvi:**\n"
            "  /monitor_add @kanal — kanal qo'shish\n"
            "  /monitor_remove @kanal — olib tashlash\n"
            "  /monitor_list — kuzatilayotgan kanallar\n"
            "  /monitor_on · /monitor_off — yoqish/o'chirish\n"
            "  /monitor_status — holat\n"
            "  /scan_now — hozir tekshirish\n\n"
            "**👥 Guruhga yuborish:**\n"
            "  Guruhda: /group_add — shu guruhni ro'yxatga kiritish\n"
            "  Shaxsiyda: /group_confirm <chat_id> — tasdiqlash\n"
            "  /group_list — ro'yxat va holat\n"
            "  /group_remove <chat_id> — o'chirish\n\n"
            "**👤 Profil:**\n"
            "  /profile — ko'rish va sozlash\n"
            "  /profile_age, /profile_grade, /profile_ielts\n"
            "  /profile_interest add|remove <nom>\n"
            "  /profile_freeonly on|off\n\n"
            "💡 Monitor har 10 daqiqada kanallarni tekshiradi va topilgan\n"
            "mos imkoniyatlarni SIZGA va tasdiqlangan guruh(lar)ga darhol yuboradi."
        )
        await event.reply(text)

    # ── /refresh ────────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/refresh$"))
    @owner_only
    async def cmd_refresh(event):
        msg = await event.reply("🔄 Dialoglar yangilanmoqda...")
        count = await _load_dialog_cache(user)
        await msg.edit(f"✅ Kesh yangilandi: {count} ta dialog.")

    # ── /monitor_add ───────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/monitor_add(?: (.+))?$"))
    @owner_only
    async def cmd_monitor_add(event):
        arg = event.pattern_match.group(1)
        if not arg:
            await event.reply(
                "ℹ️ Foydalanish:\n"
                "`/monitor_add @kanal`\n"
                "`/monitor_add -1001234567890`\n\n"
                "Bir nechta kanal: `/monitor_add @kanal1 @kanal2`"
            )
            return

        targets = arg.replace("\n", " ").split()
        was_empty = len(state.watched) == 0

        added, failed = [], []
        status = await event.reply(f"🔍 {len(targets)} ta kanal tekshirilmoqda...")

        for tgt in targets:
            tgt = tgt.strip()
            if not tgt:
                continue
            try:
                entity = await resolve_target(user, tgt)
                if entity is None:
                    failed.append(tgt)
                    continue
                cid = entity.id
                if isinstance(entity, Channel):
                    full_id = int(f"-100{cid}")
                elif isinstance(entity, Chat):
                    full_id = -cid
                else:
                    full_id = cid
                name = getattr(entity, "title", str(cid))
                state.add_channel(full_id, name)
                added.append(name)
            except Exception as e:
                log.warning(f"monitor_add {tgt}: {e}")
                failed.append(tgt)

        lines = []
        if added:
            lines.append(f"✅ Qo'shildi ({len(added)}):")
            for n in added:
                lines.append(f"  • {n}")
        if failed:
            lines.append(f"\n❌ Topilmadi ({len(failed)}):")
            for t in failed:
                lines.append(f"  • {t}")
            lines.append("Akkauntingiz shu kanalga a'zoligini tekshiring yoki /refresh qiling.")
        lines.append(f"\nJami kuzatuvda: {len(state.watched)} kanal.")
        if was_empty and added and not state.enabled:
            lines.append("\n▶️ Yoqish uchun: /monitor_on")

        await status.edit("\n".join(lines))

    # ── /monitor_remove ─────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/monitor_remove(?: (.+))?$"))
    @owner_only
    async def cmd_monitor_remove(event):
        arg = event.pattern_match.group(1)
        if not arg:
            await event.reply("ℹ️ `/monitor_remove -1001234...`\nRo'yxat: /monitor_list")
            return
        arg = arg.strip()
        removed = False
        for cid, name in list(state.watched.items()):
            if arg == cid or arg.lower() in name.lower():
                state.remove_channel(int(cid))
                await event.reply(f"🗑 Olib tashlandi: **{name}**")
                removed = True
                break
        if not removed:
            await event.reply(f"❌ Topilmadi: `{arg}`")

    # ── /monitor_list ────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/monitor_list$"))
    @owner_only
    async def cmd_monitor_list(event):
        if not state.watched:
            await event.reply("📋 Kuzatilayotgan kanal yo'q.\n`/monitor_add` bilan qo'shing.")
            return
        lines = [f"📋 **Kuzatilayotgan kanallar** ({len(state.watched)}):\n"]
        for cid, name in state.watched.items():
            lines.append(f"• {name}\n  `{cid}`")
        status = "🟢 Yoqilgan" if state.enabled else "🔴 O'chirilgan"
        lines.append(f"\nHolat: {status}")
        await event.reply("\n".join(lines))

    # ── /monitor_status ──────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/monitor_status$"))
    @owner_only
    async def cmd_monitor_status(event):
        s = state.stats
        st = state.settings
        status = "🟢 Yoqilgan" if state.enabled else "🔴 O'chirilgan"
        n_groups = len(state.confirmed_group_ids())
        await event.reply(
            f"📊 **Monitor holati**\n\n"
            f"Holat: {status}\n"
            f"Kanallar: {len(state.watched)}\n"
            f"Tasdiqlangan guruhlar: {n_groups}\n"
            f"Tekshiruv oralig'i: {st['check_interval']//60} daqiqa\n"
            f"Minimal ball: {st['min_score']}\n\n"
            f"Jami tekshiruvlar: {s['total_checks']}\n"
            f"Jami topilgan: {s['total_found']}\n"
            f"Oxirgi tekshiruv: {s['last_check'][:16] or '—'}"
        )

    # ── DIGEST/FORWARD funksiyasi (monitor darhol chaqiradi) ───
    async def on_match(opp, channel_name: str):
        text = format_opportunity(opp, channel_name)

        # 1) Egaga
        try:
            await bot.send_message(OWNER_ID, text, link_preview=False)
        except Exception as e:
            log.warning(f"Egaga yuborishda xato: {e}")
            try:
                plain = text.replace("**", "")
                await bot.send_message(OWNER_ID, plain, link_preview=False, parse_mode=None)
            except Exception as e2:
                log.error(f"Egaga umuman yuborilmadi: {e2}")

        # 2) Har bir tasdiqlangan guruhga
        for gid in state.confirmed_group_ids():
            try:
                # Yuborishdan oldin bot hali ham admin ekanini tekshiramiz —
                # huquq keyinchalik olib qo'yilgan bo'lishi mumkin.
                if not await _check_bot_is_admin(gid):
                    log.warning(f"Guruh {gid}: bot endi admin emas — o'tkazib yuborildi.")
                    continue
                await bot.send_message(gid, text, link_preview=False)
            except FloodWaitError as e:
                wait = min(int(getattr(e, "seconds", 0) or 0), 300)
                await asyncio.sleep(wait + 1)
                try:
                    await bot.send_message(gid, text, link_preview=False)
                except Exception as e2:
                    log.warning(f"Guruhga qayta urinishda ham xato ({gid}): {e2}")
            except Exception as e:
                log.warning(f"Guruhga yuborishda xato ({gid}): {e}")
                try:
                    plain = text.replace("**", "")
                    await bot.send_message(gid, plain, link_preview=False, parse_mode=None)
                except Exception as e2:
                    log.error(f"Guruhga umuman yuborilmadi ({gid}): {e2}")

    monitor = ChannelMonitor(user, state, resolve_target)

    # ── /monitor_on ──────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/monitor_on$"))
    @owner_only
    async def cmd_monitor_on(event):
        if not state.watched:
            await event.reply(
                "⚠️ Avval kanal qo'shing:\n"
                "`/monitor_add @kanal` yoki `/monitor_add -100123...`"
            )
            return
        if state.enabled:
            await event.reply("ℹ️ Monitor allaqachon yoqilgan.")
            return
        state.enabled = True
        monitor.start(on_match)
        interval = state.settings["check_interval"] // 60
        await event.reply(
            f"✅ Monitor yoqildi!\n\n"
            f"🔄 Har {interval} daqiqada {len(state.watched)} kanal tekshiriladi.\n"
            f"⭐ Minimal ball: {state.settings['min_score']} (faqat kuchli mos).\n"
            f"📤 Topilgan har bir imkoniyat darhol sizga va tasdiqlangan "
            f"guruh(lar)ga yuboriladi."
        )

    # ── /monitor_off ─────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/monitor_off$"))
    @owner_only
    async def cmd_monitor_off(event):
        state.enabled = False
        monitor.stop()
        await event.reply("🛑 Monitor o'chirildi.")

    # ── /scan_now ────────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/scan_now$"))
    @owner_only
    async def cmd_scan_now(event):
        if not state.watched:
            await event.reply("⚠️ Avval kanal qo'shing: /monitor_add")
            return
        msg = await event.reply(
            f"🔍 {len(state.watched)} kanal tekshirilmoqda...\n"
            "(birinchi marta biroz vaqt olishi mumkin)"
        )
        found = await monitor.poll_once(on_match)
        if found:
            await msg.edit(f"✅ Tekshiruv tugadi — {found} ta yangi imkoniyat yuborildi.")
        else:
            await msg.edit(
                "✅ Tekshiruv tugadi.\n"
                "Yangi imkoniyat topilmadi (yoki barchasi avval ko'rilgan).\n\n"
                "💡 Kanallar yangi qo'shilgan bo'lsa, faqat BUNDAN KEYINGI "
                "postlar kuzatiladi (eski postlar emas)."
            )

    # ── /group_add — GURUH ICHIDA yuboriladi ─────────────
    @bot.on(events.NewMessage(pattern=r"^/group_add$"))
    @owner_in_group
    async def cmd_group_add(event):
        chat = await event.get_chat()
        chat_id = event.chat_id
        title = getattr(chat, "title", str(chat_id))

        existing = state.get_group(chat_id)
        if existing and existing.get("status") == "confirmed":
            await event.reply(f"ℹ️ Bu guruh allaqachon tasdiqlangan: **{title}**")
            return

        is_admin = await _check_bot_is_admin(chat_id)
        state.add_pending_group(chat_id, title)

        if not is_admin:
            await event.reply(
                f"📋 Guruh ro'yxatga kiritildi (kutmoqda): **{title}**\n"
                f"Chat ID: `{chat_id}`\n\n"
                "⚠️ Bot bu guruhda hali ADMIN emas. Botni admin qiling, "
                "so'ng egasi shaxsiy chatda quyidagini yuborsin:\n"
                f"`/group_confirm {chat_id}`"
            )
            return

        await event.reply(
            f"📋 Guruh ro'yxatga kiritildi: **{title}**\n"
            f"Chat ID: `{chat_id}`\n\n"
            "✅ Bot bu yerda admin. Tasdiqlash uchun egasi shaxsiy chatda "
            "quyidagini yuborsin:\n"
            f"`/group_confirm {chat_id}`"
        )

    # ── /group_confirm <chat_id> — SHAXSIY chatda, faqat ega ──
    @bot.on(events.NewMessage(pattern=r"^/group_confirm(?: (-?\d+))?$"))
    @owner_only
    async def cmd_group_confirm(event):
        raw = event.pattern_match.group(1)
        if not raw:
            pending = state.pending_group_ids()
            if not pending:
                await event.reply(
                    "ℹ️ Tasdiqlanishi kutilayotgan guruh yo'q.\n"
                    "Avval guruh ichida `/group_add` yuboring."
                )
                return
            lines = ["ℹ️ Kutilayotgan guruhlar:\n"]
            for gid in pending:
                g = state.get_group(gid)
                lines.append(f"• {g['title']} — `{gid}`")
            lines.append("\nTasdiqlash: `/group_confirm <chat_id>`")
            await event.reply("\n".join(lines))
            return

        chat_id = int(raw)
        g = state.get_group(chat_id)
        if not g:
            await event.reply(
                f"❌ `{chat_id}` ro'yxatda yo'q.\n"
                "Avval o'sha guruh ichida `/group_add` yuboring."
            )
            return

        is_admin = await _check_bot_is_admin(chat_id)
        if not is_admin:
            await event.reply(
                f"❌ Bot **{g['title']}** guruhida hali admin emas.\n"
                "Avval botni guruhda admin qiling, keyin qayta urinib ko'ring."
            )
            return

        state.confirm_group(chat_id)
        await event.reply(
            f"✅ Tasdiqlandi: **{g['title']}**\n"
            "Endi bu guruh topilgan imkoniyatlarni darhol oladi."
        )
        try:
            await bot.send_message(
                chat_id,
                f"✅ Bu guruh imkoniyat monitor tomonidan tasdiqlandi.\n"
                "Endi mos imkoniyatlar shu yerga ham yuboriladi.",
            )
        except Exception as e:
            log.warning(f"Guruhga tasdiq xabari yuborilmadi ({chat_id}): {e}")

    # ── /group_list ──────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/group_list$"))
    @owner_only
    async def cmd_group_list(event):
        groups = state.groups
        if not groups:
            await event.reply(
                "📋 Ro'yxatda guruh yo'q.\n"
                "Guruh ichida `/group_add` yuboring."
            )
            return
        lines = [f"📋 **Guruhlar** ({len(groups)}):\n"]
        for gid, g in groups.items():
            icon = "✅" if g.get("status") == "confirmed" else "⏳"
            lines.append(f"{icon} {g.get('title', '?')} — `{gid}` ({g.get('status')})")
        await event.reply("\n".join(lines))

    # ── /group_remove <chat_id> ──────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/group_remove(?: (-?\d+))?$"))
    @owner_only
    async def cmd_group_remove(event):
        raw = event.pattern_match.group(1)
        if not raw:
            await event.reply("ℹ️ `/group_remove <chat_id>`\nRo'yxat: /group_list")
            return
        chat_id = int(raw)
        if state.remove_group(chat_id):
            await event.reply(f"🗑 Guruh olib tashlandi: `{chat_id}`")
        else:
            await event.reply(f"❌ `{chat_id}` ro'yxatda yo'q.")

    # ── /profile ──────────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/profile$"))
    @owner_only
    async def cmd_profile(event):
        p = state.profile
        yn = lambda b: "ha" if b else "yo'q"
        interests = ", ".join(p["interests"]) or "—"
        await event.reply(
            f"👤 **Profilingiz**\n\n"
            f"Yosh: {p['age']}\n"
            f"Sinf: {p.get('grade', '—')}\n"
            f"IELTS: {p.get('ielts', '—')}\n"
            f"Ingliz tili: {yn(p['knows_english'])}\n"
            f"Maktab o'quvchisi: {yn(p['is_pupil'])}\n"
            f"Universitet talabasi: {yn(p['is_student'])}\n"
            f"Faqat bepul: {yn(p['only_free'])}\n"
            f"Qiziqishlar: {interests}\n\n"
            f"O'zgartirish:\n"
            f"`/profile_age 16`\n"
            f"`/profile_grade 11`\n"
            f"`/profile_ielts 6.5`\n"
            f"`/profile_interest add IT`\n"
            f"`/profile_interest remove Fan`\n"
            f"`/profile_freeonly on`"
        )

    # ── /profile_age ─────────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/profile_age (\d{1,2})$"))
    @owner_only
    async def cmd_profile_age(event):
        age = int(event.pattern_match.group(1))
        state.update_profile("age", age)
        await event.reply(f"✅ Yosh: {age}")

    # ── /profile_grade ───────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/profile_grade (\d{1,2})$"))
    @owner_only
    async def cmd_profile_grade(event):
        grade = int(event.pattern_match.group(1))
        if not (1 <= grade <= 11):
            await event.reply("⚠️ Sinf 1–11 oralig'ida bo'lishi kerak.")
            return
        state.update_profile("grade", grade)
        await event.reply(f"✅ Sinf: {grade}")

    # ── /profile_ielts ───────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/profile_ielts (\d(?:[.,]\d)?)$"))
    @owner_only
    async def cmd_profile_ielts(event):
        ielts = float(event.pattern_match.group(1).replace(",", "."))
        state.update_profile("ielts", ielts)
        await event.reply(f"✅ IELTS: {ielts}")

    # ── /profile_interest ────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/profile_interest (add|remove) (.+)$"))
    @owner_only
    async def cmd_profile_interest(event):
        action = event.pattern_match.group(1)
        name = event.pattern_match.group(2).strip()
        matched = next((v for v in VALID_INTERESTS if v.lower() == name.lower()), None)
        if not matched:
            await event.reply(
                f"❌ Noma'lum qiziqish: `{name}`\n"
                f"Mavjud: {', '.join(VALID_INTERESTS)}"
            )
            return
        interests = list(state.profile["interests"])
        if action == "add":
            if matched not in interests:
                interests.append(matched)
            state.update_profile("interests", interests)
            await event.reply(f"✅ Qo'shildi: {matched}\nQiziqishlar: {', '.join(interests)}")
        else:
            if matched in interests:
                interests.remove(matched)
            state.update_profile("interests", interests)
            await event.reply(f"🗑 Olib tashlandi: {matched}\nQiziqishlar: {', '.join(interests) or '—'}")

    # ── /profile_freeonly ────────────────────────────────
    @bot.on(events.NewMessage(pattern=r"^/profile_freeonly (on|off)$"))
    @owner_only
    async def cmd_profile_freeonly(event):
        val = event.pattern_match.group(1) == "on"
        state.update_profile("only_free", val)
        await event.reply("✅ Faqat bepul: " + ("ha" if val else "yo'q"))

    return monitor, on_match


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

async def main():
    log.info("══════════════════════════════════")
    log.info("  Imkoniyat Monitor Bot START      ")
    log.info("══════════════════════════════════")

    loop = asyncio.get_running_loop()

    def _signal_handler():
        log.info("Signal qabul qilindi — to'xtatilmoqda...")
        _shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    try:
        user_client = TelegramClient(
            StringSession(USER_SESSION_STR),
            API_ID,
            API_HASH,
            connection_retries=None,
            retry_delay=5,
            auto_reconnect=True,
        )
    except Exception as e:
        log.critical(f"SESSION YAROQSIZ: {e}")
        await asyncio.sleep(3600)
        sys.exit(1)

    bot_client = TelegramClient(
        str(BASE_DIR / "bot_session"),
        API_ID,
        API_HASH,
        connection_retries=None,
        retry_delay=5,
        auto_reconnect=True,
    )

    try:
        await user_client.connect()
        if not await user_client.is_user_authorized():
            log.critical("USER_SESSION_STR yaroqsiz yoki muddati tugagan!")
            await asyncio.sleep(3600)
            sys.exit(1)

        me = await user_client.get_me()
        log.info(f"User: {me.first_name} (ID: {me.id})")

        await bot_client.start(bot_token=BOT_TOKEN)
        log.info("Bot muvaffaqiyatli ulandi.")

        log.info("Dialoglar keshga yuklanmoqda...")
        count = await _load_dialog_cache(user_client)
        log.info(f"✅ {count} ta dialog keshda.")

        state = BotState(STATE_PATH)
        monitor, on_match = register_handlers(bot_client, user_client, state)
        log.info("✅ Handlerlar tayyor. Bot kutmoqda...")

        # Agar oldin yoqilgan bo'lsa — qayta tiklaymiz
        if state.enabled and state.watched:
            monitor.start(on_match)
            log.info("✅ Monitor avtomatik tiklandi (oldin yoqilgan edi).")
        else:
            log.info("✅ Monitor tayyor (o'chiq). /monitor_on bilan yoqing.")

        async def _shutdown_watcher():
            await _shutdown_event.wait()
            log.info("Shutdown: bot_client uzilmoqda...")
            await bot_client.disconnect()

        await asyncio.gather(
            bot_client.run_until_disconnected(),
            _shutdown_watcher(),
            return_exceptions=True,
        )

    except Exception as e:
        log.exception(f"Asosiy xatolik: {e}")
    finally:
        log.info("Bot to'xtatilmoqda...")
        for client in (bot_client, user_client):
            try:
                await client.disconnect()
            except Exception:
                pass
        log.info("Bot to'xtatildi. Xayr!")


if __name__ == "__main__":
    asyncio.run(main())
