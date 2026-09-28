#!/usr/bin/env bash
# ==============================================================================
# UFQ MPP Bot — Automated Interactive Installer (Debian/Ubuntu)
# Idempotent: safe to re-run. Creates venv, installs deps, seeds DB,
# writes systemd unit, starts and verifies the service.
# ==============================================================================
set -euo pipefail

# ---------- constants ----------
APP_NAME="ufq_mpp_bot"
SERVICE_NAME="${APP_NAME}.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${INSTALL_DIR}/.venv"
ENV_FILE="${INSTALL_DIR}/.env"
RUN_USER="${SUDO_USER:-$(whoami)}"

BOT_TOKEN_RE='^[0-9]+:[A-Za-z0-9_-]+$'

# ---------- helpers ----------
c_green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
c_red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
c_yellow(){ printf '\033[0;33m%s\033[0m\n' "$1"; }
c_blue()  { printf '\033[0;34m%s\033[0m\n' "$1"; }

die() { c_red "XATOLIK: $1"; exit 1; }

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        die "Ushbu skript root (yoki sudo) huquqi bilan ishga tushirilishi kerak. Masalan: sudo bash install.sh"
    fi
}

# ---------- interactive input with validation ----------
prompt_bot_token() {
    local token=""
    if [[ -n "${BOT_TOKEN:-}" ]] && [[ "${BOT_TOKEN}" =~ ${BOT_TOKEN_RE} ]]; then
        echo "${BOT_TOKEN}"
        return
    fi
    while true; do
        read -rp "Telegram Bot Token (BotFather'dan olingan, masalan 123456:ABC-DEF...): " token
        if [[ "${token}" =~ ${BOT_TOKEN_RE} ]]; then
            echo "${token}"
            return
        fi
        c_red "Noto'g'ri format. Token '<raqamlar>:<harf-raqam>' ko'rinishida bo'lishi kerak. Qayta urinib ko'ring."
    done
}

prompt_admin_id() {
    local admin_id=""
    while true; do
        read -rp "Asosiy administrator Telegram ID raqami (butun son): " admin_id
        if [[ "${admin_id}" =~ ^[0-9]+$ ]]; then
            echo "${admin_id}"
            return
        fi
        c_red "Noto'g'ri format. Faqat raqam kiriting. Qayta urinib ko'ring."
    done
}

prompt_timezone() {
    local tz=""
    read -rp "Timezone [default: Asia/Tashkent]: " tz
    if [[ -z "${tz}" ]]; then
        echo "Asia/Tashkent"
    else
        echo "${tz}"
    fi
}

# ---------- system setup ----------
install_system_packages() {
    c_blue "==> Tizim paketlari tekshirilmoqda (python3, venv, pip, sqlite3)..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y -qq
    local pkgs=(python3 python3-venv python3-pip sqlite3)
    local to_install=()
    for pkg in "${pkgs[@]}"; do
        if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
            to_install+=("${pkg}")
        fi
    done
    if [[ ${#to_install[@]} -gt 0 ]]; then
        c_yellow "O'rnatilmoqda: ${to_install[*]}"
        apt-get install -y -qq "${to_install[@]}"
    else
        c_green "Barcha zarur paketlar allaqachon o'rnatilgan."
    fi
}

setup_venv() {
    c_blue "==> Python virtual environment sozlanmoqda..."
    if [[ ! -d "${VENV_DIR}" ]]; then
        python3 -m venv "${VENV_DIR}"
    fi
    "${VENV_DIR}/bin/pip" install --upgrade pip -q
    "${VENV_DIR}/bin/pip" install -q -r "${INSTALL_DIR}/requirements.txt"
    c_green "Virtual environment tayyor: ${VENV_DIR}"
}

write_env_file() {
    local token="$1" admin_id="$2" tz="$3"
    c_blue "==> .env fayli yozilmoqda..."
    cat > "${ENV_FILE}" <<EOF
BOT_TOKEN=${token}
ADMIN_IDS=${admin_id}
TIMEZONE=${tz}
DB_PATH=${INSTALL_DIR}/database/ufq_mpp.db
SCHEMA_PATH=${INSTALL_DIR}/database/schema.sql
EXPORT_DIR=${INSTALL_DIR}/exports
EOF
    chmod 600 "${ENV_FILE}"
    chown "${RUN_USER}:${RUN_USER}" "${ENV_FILE}" 2>/dev/null || true
    c_green ".env fayli yaratildi va himoyalandi (chmod 600)."
}

seed_database() {
    c_blue "==> Ma'lumotlar bazasi yaratilmoqda va sxema qo'llanilmoqda..."
    mkdir -p "${INSTALL_DIR}/database" "${INSTALL_DIR}/exports"
    (
        cd "${INSTALL_DIR}"
        set -a
        # shellcheck disable=SC1090
        source "${ENV_FILE}"
        set +a
        "${VENV_DIR}/bin/python" -c "
import asyncio
from database.db import init_db, close_db

async def main():
    await init_db()
    await close_db()

asyncio.run(main())
"
    )
    c_green "Ma'lumotlar bazasi tayyor (WAL rejimida)."
}

write_systemd_unit() {
    c_blue "==> systemd xizmati yaratilmoqda..."
    cat > "${SERVICE_PATH}" <<EOF
[Unit]
Description=UFQ MPP Bot (Mentor-Partner-Partner Telegram bot)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/python ${INSTALL_DIR}/bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${APP_NAME}

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1
    c_green "systemd xizmati yozildi: ${SERVICE_PATH}"
}

start_and_verify_service() {
    c_blue "==> Xizmat ishga tushirilmoqda..."
    systemctl restart "${SERVICE_NAME}"
    sleep 3
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        c_green "✅ ${SERVICE_NAME} muvaffaqiyatli ishga tushdi."
    else
        c_red "❌ Xizmat ishga tushmadi. Quyida so'nggi loglar:"
        journalctl -u "${SERVICE_NAME}" -n 50 --no-pager || true
        die "O'rnatish yakunlanmadi. Loglarni tekshiring."
    fi
    echo
    c_blue "==> So'nggi jurnal yozuvlari (journalctl):"
    journalctl -u "${SERVICE_NAME}" -n 20 --no-pager || true
}

print_summary() {
    echo
    c_green "=============================================================="
    c_green " UFQ MPP Bot muvaffaqiyatli o'rnatildi va ishga tushirildi!"
    c_green "=============================================================="
    echo "Foydali buyruqlar:"
    echo "  Holatni ko'rish:   systemctl status ${SERVICE_NAME}"
    echo "  Loglarni ko'rish:  journalctl -u ${SERVICE_NAME} -f"
    echo "  Qayta ishga tushirish: systemctl restart ${SERVICE_NAME}"
    echo "  To'xtatish:        systemctl stop ${SERVICE_NAME}"
    echo
    echo "Konfiguratsiya fayli: ${ENV_FILE}"
    echo "Ma'lumotlar bazasi:   ${INSTALL_DIR}/database/ufq_mpp.db"
}

main() {
    require_root
    c_blue "=============================================================="
    c_blue " UFQ MPP Bot — Interaktiv o'rnatish skripti"
    c_blue "=============================================================="

    local token admin_id tz
    token="$(prompt_bot_token)"
    admin_id="$(prompt_admin_id)"
    tz="$(prompt_timezone)"

    install_system_packages
    setup_venv
    write_env_file "${token}" "${admin_id}" "${tz}"
    seed_database
    write_systemd_unit
    start_and_verify_service
    print_summary
}

main "$@"
