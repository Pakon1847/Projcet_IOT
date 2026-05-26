#!/usr/bin/env bash
# ==============================================================================
#  AirGuard Pi — Raspberry Pi Setup Script
#  ติดตั้งระบบ PM2.5 Smart Air Purifier แบบ one-command
# ==============================================================================
#
#  วิธีใช้ (บน Raspberry Pi):
#    bash setup.sh
#
#  สิ่งที่ script นี้ทำ:
#    1. ตรวจสอบ OS + อัปเดต packages
#    2. เปิดใช้งาน I2C / UART (สำหรับ BME280 และ PMS5003)
#    3. ติดตั้ง Docker + Docker Compose v2
#    4. ตั้งค่า project + สร้าง .env พร้อม secret keys อัตโนมัติ
#    5. Build & start Docker services (backend, frontend, influxdb, grafana, mqtt)
#    6. ติดตั้ง Python venv สำหรับ firmware
#    7. ตั้งค่า systemd service (auto-start หลัง reboot)
#
#  Requirements:
#    - Raspberry Pi OS Bookworm หรือ Bullseye (64-bit แนะนำ)
#    - user ที่มี sudo access
#    - Internet connection
# ==============================================================================

set -euo pipefail
IFS=$'\n\t'

# ── Colors ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()     { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

section() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $*${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ── Config ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"               # script อยู่ใน root ของ project
FIRMWARE_DIR="${PROJECT_DIR}/firmware"
VENV_DIR="${FIRMWARE_DIR}/venv"
SERVICE_NAME="airguard-firmware"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
NEEDS_REBOOT=0

# ── Banner ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║   AirGuard Pi — Raspberry Pi Setup Script   ║${NC}"
echo -e "${BOLD}${CYAN}║   PM2.5 Smart Air Purifier  v1.0            ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Helper: detect boot config path ────────────────────────────────────────────
boot_config() {
    if   [[ -f /boot/firmware/config.txt ]]; then echo "/boot/firmware/config.txt"
    elif [[ -f /boot/config.txt          ]]; then echo "/boot/config.txt"
    else die "ไม่พบ /boot/config.txt — ต้องรันบน Raspberry Pi OS"
    fi
}

# ════════════════════════════════════════════════════════════════════════════════
# Step 1: ตรวจสอบ OS
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 1/7 — ตรวจสอบ OS"

if ! grep -qiE "raspberry pi|BCM2|BCM27" /proc/cpuinfo 2>/dev/null; then
    warn "ไม่พบ Raspberry Pi hardware ใน /proc/cpuinfo"
    warn "GPIO, I2C, และ UART อาจใช้งานไม่ได้บนเครื่องนี้"
    read -rp "  ต้องการดำเนินการต่อ? [y/N]: " _confirm
    [[ "${_confirm,,}" == "y" ]] || { info "ยกเลิก"; exit 0; }
fi

# ตรวจสอบ user
[[ "$(id -u)" -eq 0 ]] && die "กรุณา run script นี้ในฐานะ user ปกติ (ไม่ใช่ root)\nตัวอย่าง: bash setup.sh"

OS_DESC=$(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
success "OS: ${OS_DESC}"
success "User: ${USER} | Home: ${HOME}"
success "Project: ${PROJECT_DIR}"

# ════════════════════════════════════════════════════════════════════════════════
# Step 2: อัปเดต System + ติดตั้ง Dependencies
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 2/7 — อัปเดต System"

info "อัปเดต package list..."
sudo apt-get update -qq

info "ติดตั้ง dependencies..."
sudo apt-get install -y -qq \
    git curl wget ca-certificates gnupg \
    python3 python3-pip python3-venv python3-dev \
    i2c-tools python3-smbus \
    libgpiod2 libgpiod-dev \
    build-essential libssl-dev libffi-dev \
    2>/dev/null

success "ติดตั้ง system packages แล้ว"

# ════════════════════════════════════════════════════════════════════════════════
# Step 3: เปิดใช้งาน I2C / UART
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 3/7 — เปิดใช้งาน Hardware Interfaces"

CONFIG_FILE=$(boot_config)
info "Boot config: ${CONFIG_FILE}"

# ── I2C (BME280 + SSD1306) ─────────────────────────────────────────────────────
if grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE" 2>/dev/null; then
    success "I2C เปิดอยู่แล้ว"
else
    echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
    # โหลด module ทันที (ไม่ต้อง reboot เพื่อทดสอบ)
    sudo modprobe i2c-dev 2>/dev/null || true
    success "เปิด I2C แล้ว"
    NEEDS_REBOOT=1
fi

# ── UART (PMS5003) ─────────────────────────────────────────────────────────────
if grep -q "^enable_uart=1" "$CONFIG_FILE" 2>/dev/null; then
    success "UART เปิดอยู่แล้ว"
else
    echo "enable_uart=1" | sudo tee -a "$CONFIG_FILE" > /dev/null

    # ปิด serial console (จะขัดกับ PMS5003 ที่ใช้ /dev/ttyS0)
    if systemctl is-enabled serial-getty@ttyS0.service &>/dev/null; then
        sudo systemctl disable serial-getty@ttyS0.service
        info "ปิด serial-getty@ttyS0 แล้ว"
    fi

    # ลบ console=serial0 ออกจาก cmdline.txt (ถ้ามี)
    CMDLINE=$([ -f /boot/firmware/cmdline.txt ] && \
              echo "/boot/firmware/cmdline.txt" || echo "/boot/cmdline.txt")
    if [[ -f "$CMDLINE" ]]; then
        sudo sed -i 's/console=serial0,[0-9]* //g' "$CMDLINE"
        success "ลบ serial console ออกจาก ${CMDLINE} แล้ว"
    fi

    success "เปิด UART แล้ว"
    NEEDS_REBOOT=1
fi

# ── เพิ่ม user เข้า groups ────────────────────────────────────────────────────
GROUPS_NEEDED="i2c gpio dialout docker"
for grp in $GROUPS_NEEDED; do
    if getent group "$grp" &>/dev/null; then
        sudo usermod -aG "$grp" "$USER" 2>/dev/null && \
            info "เพิ่ม ${USER} เข้า group: ${grp}" || true
    fi
done
success "Groups: ${GROUPS_NEEDED}"

# ════════════════════════════════════════════════════════════════════════════════
# Step 4: ติดตั้ง Docker
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 4/7 — ติดตั้ง Docker"

if command -v docker &>/dev/null; then
    success "Docker ติดตั้งแล้ว: $(docker --version)"
else
    info "กำลังติดตั้ง Docker (อาจใช้เวลา 2-3 นาที)..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh > /dev/null 2>&1
    rm -f /tmp/get-docker.sh

    sudo systemctl enable docker
    sudo systemctl start docker
    success "ติดตั้ง Docker แล้ว: $(docker --version)"
    warn "ต้อง logout แล้ว login ใหม่ เพื่อให้ docker group มีผล"
    warn "หรือรัน: newgrp docker"
fi

# ตรวจสอบ Docker Compose v2
if docker compose version &>/dev/null; then
    success "Docker Compose: $(docker compose version --short 2>/dev/null || docker compose version)"
else
    info "ติดตั้ง docker-compose-plugin..."
    sudo apt-get install -y -qq docker-compose-plugin 2>/dev/null || \
        die "ติดตั้ง Docker Compose ล้มเหลว — ลอง: sudo apt install docker-compose-plugin"
    success "ติดตั้ง Docker Compose แล้ว"
fi

# ════════════════════════════════════════════════════════════════════════════════
# Step 5: ตั้งค่า .env
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 5/7 — ตั้งค่า Environment"

ENV_FILE="${PROJECT_DIR}/.env"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env มีอยู่แล้ว — ข้ามขั้นตอนนี้"
    warn "ลบไฟล์แล้วรัน script ใหม่ถ้าต้องการตั้งค่าใหม่"
else
    # Copy template
    cp "${PROJECT_DIR}/.env.prod" "$ENV_FILE"

    # ── Auto-generate secrets ──────────────────────────────────────
    GEN_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    GEN_INFLUX_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))")
    GEN_INFLUX_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(40))")

    sed -i "s|CHANGE_ME_strong_password_here|${GEN_INFLUX_PASS}|g"    "$ENV_FILE"
    sed -i "s|CHANGE_ME_long_random_token_here|${GEN_INFLUX_TOKEN}|g"  "$ENV_FILE"
    sed -i "s|CHANGE_ME_jwt_secret_here|${GEN_SECRET}|g"               "$ENV_FILE"

    # ── Interactive prompts ────────────────────────────────────────
    echo ""
    echo -e "${BOLD}กรอกข้อมูล Device (กด Enter เพื่อใช้ค่าเริ่มต้น):${NC}"
    echo ""

    read -rp "  Device ID    [pi4_home_001]         : " IN_DEVICE_ID
    read -rp "  Device Name  [เครื่องฟอกอากาศ]     : " IN_DEVICE_NAME
    read -rp "  Grafana Password [airguard2024]      : " IN_GRAFANA_PASS
    echo ""
    read -rp "  Line Notify Token (ไม่บังคับ, Enter เพื่อข้าม): " IN_LINE_TOKEN
    read -rp "  Telegram Bot Token (ไม่บังคับ)                : " IN_TELEGRAM_BOT
    read -rp "  Telegram Chat ID   (ไม่บังคับ)                : " IN_TELEGRAM_CHAT

    DEVICE_ID="${IN_DEVICE_ID:-pi4_home_001}"
    DEVICE_NAME="${IN_DEVICE_NAME:-เครื่องฟอกอากาศ}"
    GRAFANA_PASS="${IN_GRAFANA_PASS:-airguard2024}"

    sed -i "s|^DEVICE_ID=.*|DEVICE_ID=${DEVICE_ID}|"             "$ENV_FILE"
    sed -i "s|^DEVICE_NAME=.*|DEVICE_NAME=${DEVICE_NAME}|"       "$ENV_FILE"
    sed -i "s|^GRAFANA_PASSWORD=.*|GRAFANA_PASSWORD=${GRAFANA_PASS}|" "$ENV_FILE"
    sed -i "s|^MQTT_BROKER=mosquitto|MQTT_BROKER=mosquitto|"     "$ENV_FILE"

    [[ -n "$IN_LINE_TOKEN"    ]] && sed -i "s|^LINE_NOTIFY_TOKEN=.*|LINE_NOTIFY_TOKEN=${IN_LINE_TOKEN}|"      "$ENV_FILE"
    [[ -n "$IN_TELEGRAM_BOT"  ]] && sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${IN_TELEGRAM_BOT}|" "$ENV_FILE"
    [[ -n "$IN_TELEGRAM_CHAT" ]] && sed -i "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=${IN_TELEGRAM_CHAT}|"    "$ENV_FILE"

    success "สร้าง .env แล้ว (secrets generated อัตโนมัติ)"
fi

# ── Mosquitto config ────────────────────────────────────────────────────────
MOSQ_CONF="${PROJECT_DIR}/mosquitto/config/mosquitto.conf"
if [[ ! -f "$MOSQ_CONF" ]]; then
    mkdir -p "$(dirname "$MOSQ_CONF")"
    cat > "$MOSQ_CONF" << 'MOSQ_EOF'
# Mosquitto configuration — AirGuard Pi
listener 1883
listener 9001
protocol websockets
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
log_type error
log_type warning
log_type notice
MOSQ_EOF
    success "สร้าง mosquitto.conf แล้ว"
fi

# ════════════════════════════════════════════════════════════════════════════════
# Step 6: Build & Start Docker Services
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 6/7 — Build & Start Docker Services"

cd "$PROJECT_DIR"

# ตรวจสอบว่า Docker daemon รันอยู่
if ! docker info &>/dev/null; then
    info "เริ่ม Docker daemon..."
    sudo systemctl start docker
    sleep 3
fi

info "Build Docker images (อาจใช้เวลา 10-20 นาทีบน Pi)..."
info "กรุณารอ — Pi ต้องคอมไพล์ backend และ frontend..."
echo ""

if docker compose -f docker-compose.prod.yml build 2>&1; then
    success "Build images สำเร็จ"
else
    die "Build ล้มเหลว — ตรวจสอบ log ด้านบน"
fi

info "เริ่ม Docker services..."
docker compose -f docker-compose.prod.yml up -d

# รอ backend พร้อม
info "รอ backend health check..."
BACKEND_READY=0
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health &>/dev/null; then
        BACKEND_READY=1
        break
    fi
    printf "."
    sleep 3
done
echo ""

if [[ "$BACKEND_READY" -eq 1 ]]; then
    success "Backend พร้อมแล้ว ✓"
else
    warn "Backend ยังไม่ตอบสนอง — ตรวจสอบด้วย: docker compose -f docker-compose.prod.yml logs backend"
fi

success "Docker services รันอยู่แล้ว"

# ════════════════════════════════════════════════════════════════════════════════
# Step 7: ติดตั้ง Firmware
# ════════════════════════════════════════════════════════════════════════════════
section "ขั้นตอน 7/7 — ติดตั้ง Firmware"

# ── Python venv ────────────────────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    info "สร้าง Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

info "ติดตั้ง firmware Python packages..."
"${VENV_DIR}/bin/pip" install --upgrade pip -q
"${VENV_DIR}/bin/pip" install -r "${FIRMWARE_DIR}/requirements.txt" -q
success "ติดตั้ง firmware packages แล้ว"

# ── Firmware .env (MQTT ชี้ไป localhost) ──────────────────────────────────────
FIRMWARE_ENV="${FIRMWARE_DIR}/.env"
if [[ ! -f "$FIRMWARE_ENV" ]]; then
    cp "$ENV_FILE" "$FIRMWARE_ENV"
    # firmware รันบน host → ต่อ MQTT ผ่าน localhost (Docker maps 1883)
    sed -i 's|^MQTT_BROKER=mosquitto|MQTT_BROKER=localhost|' "$FIRMWARE_ENV"
    success "สร้าง firmware/.env แล้ว"
fi

# ── systemd service ────────────────────────────────────────────────────────────
info "ติดตั้ง systemd service: ${SERVICE_NAME}"

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=AirGuard Pi — PM2.5 Firmware
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${FIRMWARE_DIR}
ExecStart=${VENV_DIR}/bin/python ${FIRMWARE_DIR}/main.py
Restart=on-failure
RestartSec=10s
StartLimitIntervalSec=120s
StartLimitBurst=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=airguard-firmware
EnvironmentFile=${FIRMWARE_ENV}
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"

success "ติดตั้ง systemd service แล้ว (enabled — จะ start อัตโนมัติหลัง reboot)"
warn "ยังไม่ start firmware — เชื่อมต่อ hardware (PMS5003, BME280, OLED, Fan) ก่อนแล้วรัน:"
warn "  sudo systemctl start ${SERVICE_NAME}"

# ════════════════════════════════════════════════════════════════════════════════
# Done
# ════════════════════════════════════════════════════════════════════════════════
PI_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "pi-ip-address")

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║        Setup เสร็จสมบูรณ์ 🎉                ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}🌐 เข้าถึงระบบ:${NC}"
echo -e "  Dashboard  : ${CYAN}http://${PI_IP}/${NC}"
echo -e "  API Docs   : ${CYAN}http://${PI_IP}:8000/docs${NC}"
echo -e "  Grafana    : ${CYAN}http://${PI_IP}:3001${NC}   (admin / ดูใน .env)"
echo -e "  InfluxDB   : ${CYAN}http://${PI_IP}:8086${NC}"
echo ""
echo -e "  ${BOLD}🔧 คำสั่งที่ใช้บ่อย:${NC}"
echo "  เริ่ม firmware        : sudo systemctl start ${SERVICE_NAME}"
echo "  ดู log firmware       : journalctl -u ${SERVICE_NAME} -f"
echo "  สถานะ firmware        : sudo systemctl status ${SERVICE_NAME}"
echo "  ดู Docker logs        : docker compose -f docker-compose.prod.yml logs -f"
echo "  รีสตาร์ท Docker       : docker compose -f docker-compose.prod.yml restart"
echo "  หยุดทุก service       : docker compose -f docker-compose.prod.yml down"
echo "  อัปเดต images ใหม่    : docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo -e "  ${BOLD}📄 ไฟล์สำคัญ:${NC}"
echo "  Project config  : ${ENV_FILE}"
echo "  Firmware config : ${FIRMWARE_ENV}"
echo "  Firmware logs   : ${FIRMWARE_DIR}/logs/airguard.log"
echo ""

if [[ "$NEEDS_REBOOT" -eq 1 ]]; then
    echo -e "${YELLOW}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠  ต้อง REBOOT เพื่อเปิดใช้ I2C / UART    ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    read -rp "  Reboot ตอนนี้เลย? [y/N]: " _reboot
    if [[ "${_reboot,,}" == "y" ]]; then
        info "กำลัง reboot..."
        sudo reboot
    else
        echo "  รัน: sudo reboot  เมื่อพร้อม"
        echo ""
    fi
fi

exit 0
