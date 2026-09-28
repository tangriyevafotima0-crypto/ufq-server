#!/bin/bash
# Imkoniyat Monitor Bot — Session yaratish
# Faqat telefon raqam va SMS kod so'raydi

INSTALL_DIR="/opt/ufq_system/monitor_bot"
ENV_FILE="$INSTALL_DIR/.env"
PYTHON="$INSTALL_DIR/venv/bin/python"

echo ""
echo "════════════════════════════════════════"
echo "   Imkoniyat Monitor Bot — Telegram Login"
echo "════════════════════════════════════════"
echo ""

# .env dan mavjud qiymatlarni o'qiymiz
API_ID=$(grep "^API_ID=" "$ENV_FILE" | cut -d= -f2-)
API_HASH=$(grep "^API_HASH=" "$ENV_FILE" | cut -d= -f2-)

if [ -z "$API_ID" ] || [ -z "$API_HASH" ]; then
    echo "❌ .env da API_ID yoki API_HASH topilmadi."
    exit 1
fi

echo "  Telefon raqamingizni kiriting."
echo "  Keyin Telegramga kod keladi."
echo ""
printf "  Telefon (+998...): "
read -r PHONE

if [ -z "$PHONE" ]; then
    echo "❌ Telefon raqam bo'sh."
    exit 1
fi

SESS_TEMP="$(mktemp /tmp/monitor_sess.XXXXXXXXXX)"
chmod 600 "$SESS_TEMP"
echo ""
echo "  ⏳ Telegram bilan ulanilmoqda..."
echo ""

"$PYTHON" "$INSTALL_DIR/gen_session.py" \
    "$API_ID" "$API_HASH" "$PHONE" "$SESS_TEMP"

if [ ! -s "$SESS_TEMP" ]; then
    echo ""
    echo "❌ Session yaratilmadi."
    echo "   Telefon raqam to'g'rimi? (+998XXXXXXXXX)"
    rm -f "$SESS_TEMP"
    exit 1
fi

SESSION=$(cat "$SESS_TEMP")
rm -f "$SESS_TEMP"

# USER_SESSION_STR ni .env ga xavfsiz yozamiz (Python — sed maxsus belgilardan xoli)
SESS_VAL_TEMP="$(mktemp /tmp/sess_val.XXXXXXXXXX)"
chmod 600 "$SESS_VAL_TEMP"
printf '%s' "$SESSION" > "$SESS_VAL_TEMP"

sudo "$PYTHON" - "$ENV_FILE" "$SESS_VAL_TEMP" << 'PYEOF'
import sys
env_path, sess_path = sys.argv[1], sys.argv[2]
with open(sess_path) as f:
    session = f.read().strip()

lines = []
found = False
try:
    with open(env_path) as f:
        for line in f:
            if line.startswith("USER_SESSION_STR="):
                lines.append(f"USER_SESSION_STR={session}\n")
                found = True
            else:
                lines.append(line)
except FileNotFoundError:
    pass

if not found:
    lines.append(f"USER_SESSION_STR={session}\n")

with open(env_path, "w") as f:
    f.writelines(lines)
PYEOF

rm -f "$SESS_VAL_TEMP"
sudo chmod 600 "$ENV_FILE"
sudo chown ubuntu:ubuntu "$ENV_FILE"

echo ""
echo "✅ Session saqlandi!"
echo ""
