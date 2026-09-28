#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Imkoniyat Monitor Bot — Robust Deploy
#  Bir buyruq bilan: fayllar → venv → paketlar → session →
#  systemd servis → health-check. Xatoga chidamli, idempotent.
# ═══════════════════════════════════════════════════════════
set -euo pipefail

# ── Sozlamalar ─────────────────────────────────────────────
INSTALL_DIR="/opt/ufq_system/monitor_bot"
SERVICE_NAME="monitor-bot"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_MIN_MINOR=8                       # Python 3.8+ talab
HEALTH_WAIT=20                       # health-check kutish (soniya)

# Ranglar (terminal qo'llab-quvvatlasa)
if [ -t 1 ]; then
    R=$'\e[31m'; G=$'\e[32m'; Y=$'\e[33m'; B=$'\e[36m'; N=$'\e[0m'
else
    R=""; G=""; Y=""; B=""; N=""
fi
say()  { echo "${B}▶${N} $*"; }
ok()   { echo "${G}✅${N} $*"; }
warn() { echo "${Y}⚠️ ${N} $*"; }
die()  { echo "${R}❌ $*${N}" >&2; exit 1; }

# ── Xato tutqichi: qayerda uzilganini ko'rsatadi ───────────
trap 'die "Deploy xato bilan to'\''xtadi (satr $LINENO). Yuqoridagi xabarni o'\''qing."' ERR

echo ""
echo "══════════════════════════════════"
echo "   Imkoniyat Monitor Bot — Deploy "
echo "══════════════════════════════════"
echo ""

# ── 0. sudo bormi? ─────────────────────────────────────────
if command -v sudo &>/dev/null; then
    SUDO="sudo"
else
    [ "$(id -u)" -eq 0 ] || die "sudo topilmadi va root ham emassiz."
    SUDO=""
fi

# ── 1. Xizmat egasi bo'ladigan foydalanuvchini ANIQLAYMIZ ──
RUN_USER="${SUDO_USER:-$(logname 2>/dev/null || true)}"
if [ -z "$RUN_USER" ] || [ "$RUN_USER" = "root" ]; then
    RUN_USER="$(awk -F: '$3>=1000 && $3<65534 {print $1; exit}' /etc/passwd)"
fi
[ -z "$RUN_USER" ] && RUN_USER="root"
RUN_GROUP="$(id -gn "$RUN_USER" 2>/dev/null || echo "$RUN_USER")"
ok "Servis foydalanuvchisi: ${RUN_USER}:${RUN_GROUP}"

# ── 2. Kerakli tizim paketlarini tekshirib, yetishmasa o'rnatamiz ──
say "Tizim talablari tekshirilmoqda..."
APT_NEED=()
command -v python3 &>/dev/null || APT_NEED+=("python3")
python3 -c "import venv" 2>/dev/null || APT_NEED+=("python3-venv")
python3 -c "import ensurepip" 2>/dev/null || APT_NEED+=("python3-venv")
command -v unzip &>/dev/null || APT_NEED+=("unzip")

if [ "${#APT_NEED[@]}" -gt 0 ]; then
    UNIQ=$(printf "%s\n" "${APT_NEED[@]}" | sort -u | tr '\n' ' ')
    if command -v apt-get &>/dev/null; then
        warn "Yetishmayapti: $UNIQ — o'rnatilmoqda..."
        $SUDO apt-get update -qq
        # shellcheck disable=SC2086
        $SUDO apt-get install -y -qq $UNIQ || die "apt-get o'rnatishda xato: $UNIQ"
    else
        die "Quyidagilar yetishmayapti va apt-get yo'q: $UNIQ (qo'lda o'rnating)"
    fi
fi

# Python versiyasini tekshiramiz
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
[ "$PY_MINOR" -ge "$PY_MIN_MINOR" ] || \
    die "Python 3.${PY_MIN_MINOR}+ kerak (topildi: 3.${PY_MINOR})."
ok "Python 3.${PY_MINOR}"

# Manba fayllar joyidami?
[ -f "$SRC_DIR/bot.py" ] || die "bot.py topilmadi ($SRC_DIR). ZIP to'liq ochilganmi?"

# ── 3. Fayllarni o'rnatamiz ────────────────────────────────
say "Fayllar o'rnatilmoqda → $INSTALL_DIR"
$SUDO mkdir -p "$INSTALL_DIR"

CODE_FILES=(
    bot.py gen_session.py requirements.txt setup_env.sh monitor-bot.service
    parser.py matcher.py monitor.py storage.py
)
for f in "${CODE_FILES[@]}"; do
    [ -f "$SRC_DIR/$f" ] && $SUDO cp "$SRC_DIR/$f" "$INSTALL_DIR/$f"
done
$SUDO chmod +x "$INSTALL_DIR/setup_env.sh"

# ── 4. .env logikasi (session saqlanadi) ───────────────────
#   Serverda .env BOR  → tegmaymiz, lekin avval BACKUP olamiz.
#   Serverda .env YO'Q → ZIP namunasini yoki .env.example ni qo'yamiz.
if [ -f "$INSTALL_DIR/.env" ]; then
    $SUDO cp -a "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.bak.$(date +%Y%m%d_%H%M%S)"
    ok "Mavjud .env saqlandi (backup olindi, tegilmadi)"
else
    if [ -f "$SRC_DIR/.env" ]; then
        $SUDO cp "$SRC_DIR/.env" "$INSTALL_DIR/.env"
        warn ".env namunasi o'rnatildi — tokenlarni to'ldiring."
    elif [ -f "$SRC_DIR/.env.example" ]; then
        $SUDO cp "$SRC_DIR/.env.example" "$INSTALL_DIR/.env"
        warn ".env.example dan nusxa olindi — tokenlarni to'ldiring."
    else
        $SUDO touch "$INSTALL_DIR/.env"
        warn "Bo'sh .env yaratildi — tokenlarni to'ldiring."
    fi
fi

$SUDO chmod 600 "$INSTALL_DIR/.env"
$SUDO chown -R "$RUN_USER:$RUN_GROUP" "$INSTALL_DIR"
ok "Fayllar tayyor"

# ── 4.5. Kerakli tokenlarni INTERAKTIV so'rab, .env ga yozamiz ─
#   Yetishmagan yoki placeholder qiymatlarni topib, foydalanuvchidan
#   so'raymiz va o'zimiz xavfsiz joylashtiramiz (qo'lda nano ochish shart emas).
ENV_FILE="$INSTALL_DIR/.env"

env_get() {
    $SUDO grep "^$1=" "$ENV_FILE" 2>/dev/null | tail -n1 | cut -d= -f2- || true
}

env_set() {
    local key="$1" val="$2"
    $SUDO python3 - "$ENV_FILE" "$key" "$val" << 'PYEOF'
import sys
env_path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
lines = []
found = False
try:
    with open(env_path) as f:
        for line in f:
            if line.startswith(key + "="):
                lines.append(f"{key}={val}\n")
                found = True
            else:
                lines.append(line)
except FileNotFoundError:
    pass
if not found:
    lines.append(f"{key}={val}\n")
with open(env_path, "w") as f:
    f.writelines(lines)
PYEOF
}

is_placeholder() {
    case "$1" in
        ""|"12345678"|"abcdef1234567890abcdef1234567890"|"1234567890:AABBCCDDaabbccdd..."|"123456789")
            return 0 ;;
        *) return 1 ;;
    esac
}

ask_credential() {
    # $1=key  $2=so'rov matni  $3=validatsiya regex (bo'sh=yo'q)  $4=maslahat
    local key="$1" prompt="$2" pattern="$3" hint="$4"
    local current value
    current="$(env_get "$key")"
    if ! is_placeholder "$current"; then
        ok "$key allaqachon .env da bor — o'tkazib yuborildi."
        return
    fi
    while true; do
        echo ""
        echo "  $hint"
        printf "  %s: " "$prompt"
        read -r value
        value="$(echo -n "$value" | tr -d '[:space:]' 2>/dev/null || echo -n "$value")"
        if [ -z "$value" ]; then
            warn "Bo'sh bo'lishi mumkin emas — qayta kiriting."
            continue
        fi
        if [ -n "$pattern" ] && ! echo "$value" | grep -qE "$pattern"; then
            warn "Format noto'g'ri ko'rinadi — qayta tekshirib kiriting."
            continue
        fi
        env_set "$key" "$value"
        ok "$key saqlandi."
        break
    done
}

NEED_CREDS=0
for k in API_ID API_HASH BOT_TOKEN OWNER_ID; do
    v="$(env_get "$k")"
    if is_placeholder "$v"; then NEED_CREDS=1; fi
done

if [ "$NEED_CREDS" -eq 1 ] && [ -t 0 ]; then
    echo ""
    echo "── Bot tokenlarini kiriting ─────────────────────"
    echo "   (bir marta so'raladi, o'zi .env ga xavfsiz yoziladi)"
    ask_credential "API_ID" "API_ID (my.telegram.org)" '^[0-9]+$' \
        "my.telegram.org → API development tools dagi API ID (faqat raqam)."
    ask_credential "API_HASH" "API_HASH (my.telegram.org)" '^[a-fA-F0-9]{32}$' \
        "my.telegram.org dagi API Hash (32 belgili harf+raqam)."
    ask_credential "BOT_TOKEN" "BOT_TOKEN (@BotFather)" '^[0-9]+:[A-Za-z0-9_-]+$' \
        "@BotFather dan olingan bot tokeni (masalan 123456:AAExxxx)."
    ask_credential "OWNER_ID" "OWNER_ID (sizning Telegram ID)" '^[0-9]+$' \
        "Bot tokeningizni @BotFather orqali olgach botga /start yuboring — \n  yoki @userinfobot ga yozib shaxsiy Telegram ID raqamingizni oling."
    $SUDO chmod 600 "$ENV_FILE"
    ok "Barcha tokenlar .env ga yozildi."
elif [ "$NEED_CREDS" -eq 1 ]; then
    warn "Interaktiv terminal topilmadi — tokenlar so'ralmadi."
    warn "Qo'lda to'ldiring: $ENV_FILE  keyin qayta: bash $0"
else
    ok "Barcha tokenlar (API_ID/API_HASH/BOT_TOKEN/OWNER_ID) allaqachon mavjud."
fi

# ── 5. Virtual environment + paketlar (retry bilan) ────────
say "Virtual environment tayyorlanmoqda..."
cd "$INSTALL_DIR"
if [ ! -x "venv/bin/python" ]; then
    $SUDO -u "$RUN_USER" python3 -m venv venv || die "venv yaratilmadi."
fi

pip_install() {
    $SUDO -u "$RUN_USER" ./venv/bin/pip install --upgrade pip --quiet
    $SUDO -u "$RUN_USER" ./venv/bin/pip install -r requirements.txt --quiet
}
say "Paketlar o'rnatilmoqda (telethon, dotenv, cryptg)..."
if ! pip_install; then
    warn "Birinchi urinish muvaffaqiyatsiz — 5s dan keyin qayta..."
    sleep 5
    pip_install || die "Paketlarni o'rnatib bo'lmadi (internet/PyPI tekshiring)."
fi
ok "Paketlar tayyor"

# ── 6. Session tekshirish ──────────────────────────────────
CURRENT_SESSION=$(env_get "USER_SESSION_STR")
API_ID_NOW=$(env_get "API_ID")
if [ -z "$CURRENT_SESSION" ]; then
    if is_placeholder "$API_ID_NOW"; then
        warn "API_ID/API_HASH hali yo'q — session so'ralmadi."
        warn "To'ldirgach:  bash $INSTALL_DIR/setup_env.sh  keyin qayta deploy."
    elif [ -t 0 ]; then
        echo ""; echo "── Telegram Login ──────────────────────────"
        bash "$INSTALL_DIR/setup_env.sh" || warn "Login yakunlanmadi — keyin qayta urinib ko'ring."
    else
        warn "Interaktiv terminal yo'q — session so'ralmadi."
        warn "Keyin qo'lda:  bash $INSTALL_DIR/setup_env.sh"
    fi
else
    ok "Session mavjud"
fi

# ── 7. systemd unit'ni DINAMIK yaratamiz (to'g'ri user bilan) ──
say "systemd servis sozlanmoqda..."
$SUDO tee "/etc/systemd/system/$SERVICE_NAME.service" >/dev/null <<UNIT
[Unit]
Description=Imkoniyat Monitor Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10
StartLimitIntervalSec=60
StartLimitBurst=5
TimeoutStopSec=30
KillMode=mixed
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
UNIT

$SUDO systemctl daemon-reload
$SUDO systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
$SUDO systemctl restart "$SERVICE_NAME"

# ── 8. Health-check (aktiv kutish + log tahlili) ───────────
say "Bot ishga tushishi kutilmoqda (${HEALTH_WAIT}s)..."
HEALTHY=0
for _ in $(seq 1 "$HEALTH_WAIT"); do
    if $SUDO systemctl is-active --quiet "$SERVICE_NAME"; then
        HEALTHY=1
        break
    fi
    sleep 1
done
# Yakuniy holatni qat'iy tekshiramiz (erta break bo'lsa ham qayta tasdiqlaymiz)
if $SUDO systemctl is-active --quiet "$SERVICE_NAME"; then HEALTHY=1; else HEALTHY=0; fi

if [ "$HEALTHY" -eq 1 ]; then
    ok "Bot muvaffaqiyatli ishlayapti!"
else
    echo ""; warn "Bot ishga tushmadi. Sabab aniqlanmoqda..."; echo ""
    LOGS=$($SUDO journalctl -u "$SERVICE_NAME" -n 40 --no-pager 2>/dev/null || true)

    if echo "$LOGS" | grep -qiE "Incorrect padding|SESSION YAROQSIZ|yaroqsiz|Unauthorized|AuthKey"; then
        warn "SABAB: Session buzuq yoki muddati tugagan → qayta login."
        $SUDO sed -i 's/^USER_SESSION_STR=.*/USER_SESSION_STR=/' "$INSTALL_DIR/.env"
        bash "$INSTALL_DIR/setup_env.sh" || true
        say "Bot qayta ishga tushirilmoqda..."
        $SUDO systemctl restart "$SERVICE_NAME"; sleep 5
        if $SUDO systemctl is-active --quiet "$SERVICE_NAME"; then
            ok "Bot endi ishlayapti!"; HEALTHY=1
        fi
    elif echo "$LOGS" | grep -qiE "topilmadi yoki bo'sh|BOT_TOKEN|API_ID|OWNER_ID|Invalid token"; then
        warn "SABAB: .env to'ldirilmagan yoki token noto'g'ri."
        echo "   Tuzatish:  nano $INSTALL_DIR/.env   keyin:  bash $0"
    fi

    if [ "$HEALTHY" -ne 1 ]; then
        echo ""; echo "Oxirgi loglar:"
        echo "$LOGS" | tail -n 15
    fi
fi

# ── 9. Yakuniy ma'lumot ────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  Holat:    ${SUDO} systemctl status $SERVICE_NAME"
echo "  Loglar:   ${SUDO} journalctl -u $SERVICE_NAME -f"
echo "  Restart:  ${SUDO} systemctl restart $SERVICE_NAME"
echo "  Session:  bash $INSTALL_DIR/setup_env.sh"
echo "════════════════════════════════════════════"
echo ""
[ "$HEALTHY" -eq 1 ] || exit 1
