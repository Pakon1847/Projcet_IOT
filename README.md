# 💨 AirGuard Pi — PM2.5 Smart Air Purifier System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TFLite-LSTM-FF6F00?logo=tensorflow&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-4B-C51A4A?logo=raspberrypi&logoColor=white)

**ระบบเครื่องฟอกอากาศอัจฉริยะที่ตรวจวัด PM2.5 แบบ Real-time ควบคุมพัดลมอัตโนมัติด้วย AI  
และแสดงผลผ่าน Web Dashboard บน Raspberry Pi 4**

มาตรฐาน: กรมควบคุมมลพิษ (PCD) ประกาศ พ.ศ. 2566

</div>

---

## 📋 สารบัญ

- [ภาพรวมระบบ](#-ภาพรวมระบบ)
- [ฟีเจอร์หลัก](#-ฟีเจอร์หลัก)
- [สถาปัตยกรรมระบบ](#-สถาปัตยกรรมระบบ)
- [Hardware](#-hardware)
- [Software Stack](#-software-stack)
- [โครงสร้างโปรเจกต์](#-โครงสร้างโปรเจกต์)
- [เริ่มต้นใช้งาน (Development)](#-เริ่มต้นใช้งาน-development)
- [Deploy บน Raspberry Pi](#-deploy-บน-raspberry-pi)
- [มาตรฐาน AQI ไทย](#-มาตรฐาน-aqi-ไทย)
- [AI / Machine Learning](#-ai--machine-learning)
- [API Reference](#-api-reference)
- [อ้างอิง](#-อ้างอิง)

---

## 🌟 ภาพรวมระบบ

AirGuard Pi เป็นระบบ IoT ที่รวม **hardware sensor**, **embedded firmware**, **cloud-like backend**, และ **web frontend** เข้าด้วยกันบน Raspberry Pi 4 เพียงเครื่องเดียว โดยใช้ MQTT เป็น message broker เชื่อมทุก component เข้าด้วยกันแบบ real-time

```
PMS5003 ──┐                        ┌── PWM → MOSFET → พัดลม HEPA
BME280  ──┤── firmware/main.py ──→ MQTT ──┤── SSD1306 OLED Display
          └── Thai AQI Calculator          └── FastAPI Backend
                                                    │
                                          InfluxDB (time-series)
                                          SQLite   (users/alerts)
                                                    │
                                           React Dashboard
                                           Grafana Monitoring
```

---

## ✨ ฟีเจอร์หลัก

| ฟีเจอร์ | รายละเอียด |
|---------|-----------|
| 📊 **Real-time Dashboard** | แสดง PM2.5, AQI, อุณหภูมิ, ความชื้น — อัปเดตทุก 10 วินาที ผ่าน WebSocket |
| 🌀 **Auto Fan Control** | ควบคุมความเร็วพัดลม PWM อัตโนมัติตามระดับ AQI (5 ระดับ PCD 2566) |
| 🤖 **LSTM Prediction** | พยากรณ์ค่า PM2.5 ล่วงหน้า 1 ชั่วโมง ด้วย LSTM → TFLite บน Pi |
| 💬 **AI Chat** | ถาม-ตอบคุณภาพอากาศด้วย Ollama + Phi-3 Mini (Local LLM) |
| 🔔 **Smart Alerts** | แจ้งเตือนผ่าน Line Notify / Telegram เมื่อ PM2.5 เกินค่ามาตรฐาน |
| 📈 **History & Analytics** | กราฟ PM2.5 ย้อนหลัง + Grafana dashboard |
| 🖥️ **OLED Display** | แสดงค่า PM2.5, AQI, Fan speed บนหน้าจอของตัวเครื่องแบบ offline |
| 🔐 **Authentication** | ระบบ Login/Register ด้วย JWT token |

---

## 🏗️ สถาปัตยกรรมระบบ

```
┌─────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi 4                           │
│                                                                 │
│  ┌──────────────┐    UART     ┌──────────────────────────────┐  │
│  │   PMS5003    │────────────▶│                              │  │
│  │  PM2.5 Sensor│             │     firmware/main.py         │  │
│  └──────────────┘    I2C      │  (Python Threads)            │  │
│  ┌──────────────┐────────────▶│  Thread-1: SensorLoop        │  │
│  │    BME280    │             │  Thread-2: FanController      │  │
│  │Temp/Hum/Press│             │  Thread-3: OLEDDisplay        │  │
│  └──────────────┘             │  Watchdog: Health Monitor     │  │
│                               └──────────┬───────────────────┘  │
│                                          │ MQTT publish          │
│                               ┌──────────▼───────────────────┐  │
│  ┌──────────────┐   PWM/GPIO  │   Mosquitto MQTT Broker       │  │
│  │  HEPA Fan    │◀────────────│   (Docker Container)          │  │
│  │  + MOSFET    │  subscribe  └──────────┬───────────────────┘  │
│  └──────────────┘                        │ subscribe             │
│  ┌──────────────┐   I2C                  ▼                      │
│  │ SSD1306 OLED │◀─────────── FastAPI Backend (Docker)          │
│  │   Display    │             ├── InfluxDB (time-series)         │
│  └──────────────┘             ├── SQLite (users/alerts)          │
│                               └── WebSocket Manager             │
│                                          │                      │
│                               ┌──────────▼───────────────────┐  │
│                               │   React Frontend (Docker)     │  │
│                               │   Nginx → http://pi-ip/       │  │
│                               └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Hardware

| # | อุปกรณ์ | รุ่น | ราคา (บาท) | หมายเหตุ |
|---|---------|------|-----------|---------|
| 1 | **Raspberry Pi 4 Model B 4GB** | Official | 2,200–2,800 | CPU หลักของระบบ |
| 2 | **Power Supply Pi 4** | Official 5V/3A USB-C | 350–450 | ใช้ของแท้เท่านั้น |
| 3 | **MicroSD Card** | SanDisk 32GB A1 | 200–300 | ติดตั้ง OS |
| 4 | **USB SSD** ⭐ | Samsung T7 250GB | 1,200–1,500 | Boot จาก SSD แทน SD (กัน DB corrupt) |
| 5 | **PM2.5 Sensor PMS5003** | Plantower | 350–500 | UART, ความแม่นยำสูง |
| 6 | **BME280** | Generic I2C Module | 80–150 | วัด Temp / Humidity / Pressure |
| 7 | **HEPA Fan (DC 12V)** | พร้อม HEPA H13 | 400–800 | กรอง PM2.5 ได้ >99.97% |
| 8 | **MOSFET Module** | IRF520 / BTS7960 | 50–150 | ควบคุม PWM Fan Speed |
| 9 | **DC Power Supply 12V 2A** | Generic Adapter | 150–250 | จ่ายไฟพัดลม |
| 10 | **OLED Display 128×64** | SSD1306 I2C | 80–150 | แสดงค่าบนตัวเครื่อง |
| 11 | **Jumper Wires + Breadboard** | Generic | 100–200 | ต่อวงจร prototype |
| 12 | **Pi 4 Case + Heatsink** | With fan | 200–350 | ป้องกัน thermal throttling |
| | | **รวม** | **~5,400–7,700 บาท** | |

### วงจรเชื่อมต่อ GPIO

```
Raspberry Pi 4 GPIO (BCM numbering)
──────────────────────────────────────
PMS5003 TX   → GPIO 15 (RXD / UART)
PMS5003 RX   → GPIO 14 (TXD / UART)
PMS5003 VCC  → 5V Pin
PMS5003 GND  → GND

BME280 SDA   → GPIO 2  (I2C SDA)
BME280 SCL   → GPIO 3  (I2C SCL)
BME280 VCC   → 3.3V Pin
BME280 GND   → GND

SSD1306 SDA  → GPIO 2  (I2C SDA, shared)
SSD1306 SCL  → GPIO 3  (I2C SCL, shared)
SSD1306 VCC  → 3.3V Pin
SSD1306 GND  → GND

MOSFET Gate  → GPIO 18 (PWM0)
MOSFET VCC   → 12V External PSU
MOSFET GND   → GND (shared with Pi)
Fan +        → 12V External PSU
Fan -        → MOSFET Drain
```

---

## 🛠️ Software Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Firmware** | Python | 3.11 |
| **Firmware** | paho-mqtt | 2.0 |
| **Firmware** | adafruit-circuitpython-bme280 | latest |
| **Firmware** | adafruit-circuitpython-ssd1306 | latest |
| **Firmware** | RPi.GPIO | latest |
| **Backend** | FastAPI | 0.111 |
| **Backend** | InfluxDB Client | 1.45 |
| **Backend** | SQLAlchemy + SQLite | 2.0 |
| **Backend** | Pydantic | 2.x |
| **Frontend** | React | 18 |
| **Frontend** | TypeScript | 5 |
| **Frontend** | Vite | 5 |
| **Frontend** | Tailwind CSS | 3 |
| **Frontend** | Recharts | 2 |
| **ML** | TensorFlow | 2.16 |
| **ML** | TFLite (Flex Delegate) | — |
| **Infrastructure** | Docker Compose | v2 |
| **Infrastructure** | Mosquitto MQTT | 2.0 |
| **Infrastructure** | InfluxDB | 2.7 |
| **Infrastructure** | Grafana | 10.4 |
| **Infrastructure** | Nginx | alpine |

---

## 📁 โครงสร้างโปรเจกต์

```
pm25-project/
│
├── 📄 .env                        ← Environment config (สร้างจาก .env.prod)
├── 📄 .env.example                ← Template สำหรับ dev
├── 📄 .env.prod                   ← Template สำหรับ production Pi
├── 📄 .gitignore
├── 📄 README.md
│
├── 🐳 docker-compose.dev.yml      ← Development (PC, HMR, hot-reload)
├── 🐳 docker-compose.prod.yml     ← Production (Raspberry Pi)
│
├── 🔧 setup.sh                    ← One-command Pi setup script
├── 📄 mock_sensor.py              ← จำลอง sensor ทดสอบโดยไม่มี hardware
├── 📄 test_pipeline.py            ← ทดสอบ MQTT → Backend → InfluxDB pipeline
├── 📄 setup-dev.ps1               ← Dev setup สำหรับ Windows
│
├── backend/                       ← FastAPI
│   ├── app/
│   │   ├── main.py                ← Entry point + routers registration
│   │   ├── config.py              ← Settings (env vars)
│   │   ├── database.py            ← InfluxDB + SQLite connections
│   │   ├── mqtt_subscriber.py     ← Subscribe MQTT → write InfluxDB
│   │   ├── models/                ← SQLAlchemy ORM
│   │   │   ├── user.py
│   │   │   ├── device.py
│   │   │   ├── alert_rule.py
│   │   │   └── alert_log.py
│   │   ├── routers/               ← API endpoints
│   │   │   ├── auth.py            ← POST /api/auth/login, /register
│   │   │   ├── sensor.py          ← GET /api/sensor/latest, /history
│   │   │   ├── fan.py             ← GET/POST /api/fan/speed
│   │   │   ├── alert.py           ← CRUD /api/alerts/rules
│   │   │   └── ai.py              ← POST /api/ai/predict, /chat
│   │   ├── services/
│   │   │   ├── aqi.py             ← Thai AQI calculator (PCD 2566)
│   │   │   ├── fan_control.py     ← Fan speed logic
│   │   │   ├── influx.py          ← InfluxDB query helpers
│   │   │   └── notification.py    ← Line Notify + Telegram
│   │   └── ws/
│   │       └── manager.py         ← WebSocket broadcast manager
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      ← React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx                ← Router + auth guard
│   │   ├── main.tsx
│   │   ├── index.css              ← Tailwind + custom animations
│   │   ├── api/                   ← Axios API clients
│   │   │   ├── auth.ts
│   │   │   ├── sensor.ts
│   │   │   ├── fan.ts
│   │   │   ├── alert.ts
│   │   │   └── ai.ts
│   │   ├── components/
│   │   │   ├── NavBar.tsx         ← Glassmorphism navigation
│   │   │   ├── StatCard.tsx       ← Animated number cards
│   │   │   ├── AQIGauge.tsx       ← AQI gauge visualisation
│   │   │   ├── PM25Chart.tsx      ← Recharts PM2.5 history
│   │   │   ├── FanControl.tsx     ← Fan speed slider
│   │   │   └── ParticleBackground.tsx ← Canvas particle network
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts    ← Real-time data hook
│   │   │   └── useCountUp.ts      ← Animated number counter
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── HistoryPage.tsx
│   │   │   ├── FanPage.tsx
│   │   │   ├── AlertsPage.tsx
│   │   │   ├── AIChatPage.tsx
│   │   │   └── SystemFlowPage.tsx ← Interactive architecture diagram
│   │   ├── store/
│   │   │   └── useStore.ts        ← Zustand global state
│   │   └── lib/
│   │       └── aqi.ts             ← AQI color/label helpers
│   ├── nginx.conf                 ← SPA fallback + /api proxy
│   ├── Dockerfile                 ← Multi-stage build (node → nginx)
│   └── package.json
│
├── firmware/                      ← Raspberry Pi 4
│   ├── main.py                    ← Entry point (3 threads + watchdog)
│   ├── sensor_reader.py           ← PMS5003 + BME280 driver
│   ├── fan_controller.py          ← PWM fan via RPi.GPIO
│   ├── oled_display.py            ← SSD1306 128×64 display
│   ├── config.py                  ← Config from .env
│   ├── requirements.txt
│   └── utils/
│       └── aqi_local.py           ← Thai AQI (ออฟไลน์ ไม่ต้องต่อ internet)
│
├── ml/                            ← Machine Learning
│   ├── pm25_lstm.ipynb            ← Training notebook (JupyterLab)
│   ├── requirements.txt
│   ├── data/
│   │   ├── synthetic_pm25.csv     ← Training data (synthetic 30 วัน)
│   │   ├── training_curves.png    ← Loss curves
│   │   └── forecast_h1.png        ← Prediction vs actual
│   ├── models/
│   │   ├── pm25_lstm.keras        ← Trained Keras model
│   │   ├── best_lstm.keras        ← Best checkpoint (EarlyStopping)
│   │   ├── pm25_lstm.tflite       ← TFLite FP32 (139 KB)
│   │   ├── pm25_lstm_int8.tflite  ← TFLite INT8 Dynamic Range (60 KB)
│   │   └── model_meta.json        ← Scaler params + model info
│   └── src/
│       └── ml_predictor.py        ← Inference class (ใช้ใน backend)
│
├── mosquitto/
│   └── config/
│       └── mosquitto.conf         ← MQTT broker config
│
└── deploy/
    └── airguard-firmware.service  ← systemd unit (auto-start firmware)
```

---

## 🚀 เริ่มต้นใช้งาน (Development)

> ทดสอบบน PC ได้เลย ไม่ต้องมี Raspberry Pi

### Prerequisites
- Docker Desktop + Docker Compose v2
- Python 3.11+ (สำหรับ mock sensor)
- Node.js 20+ (ถ้าจะรัน frontend นอก Docker)

### 1. Clone และตั้งค่า

```bash
git clone <your-repo-url>
cd pm25-project
```

### 2. รัน Docker services

```powershell
# Windows
.\setup-dev.ps1

# หรือรันตรง
docker compose -f docker-compose.dev.yml up -d --build
```

| Service | URL | Credentials |
|---------|-----|-------------|
| 🌐 Frontend | http://localhost:5173 | — |
| ⚡ Backend API | http://localhost:8000/docs | — |
| 📊 Grafana | http://localhost:3001 | admin / admin |
| 🗃️ InfluxDB | http://localhost:8086 | admin / adminpass123 |
| 📡 MQTT | localhost:1883 | — |

### 3. จำลองข้อมูล Sensor

```bash
# สร้าง virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
.\venv\Scripts\activate    # Windows

pip install paho-mqtt

# รัน mock sensor (จำลองค่า PM2.5 แบบต่างๆ)
python mock_sensor.py --scenario full --interval 3
```

Scenarios ที่มี:
- `normal` — PM2.5 ปกติ (~15 µg/m³)
- `moderate` — ปานกลาง (~50 µg/m³)
- `high` — สูง (~120 µg/m³)
- `full` — วนผ่านทุกระดับ

### 4. ทดสอบ Pipeline

```bash
python test_pipeline.py
```

---

## 🍓 Deploy บน Raspberry Pi

### วิธีที่ 1: One-Command Setup (แนะนำ)

```bash
# วาง project ไว้ใน ~/airguard แล้วรัน
bash setup.sh
```

Script จะทำทุกอย่างให้อัตโนมัติ:
- เปิด I2C + UART
- ติดตั้ง Docker
- ตั้งค่า `.env` พร้อม generate secret keys
- Build & start Docker containers
- ติดตั้ง Python venv สำหรับ firmware
- ตั้งค่า systemd auto-start

### วิธีที่ 2: Manual

```bash
# 1. Enable interfaces
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial 0

# 2. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. ตั้งค่า environment
cp .env.prod .env
nano .env   # แก้ไข INFLUX_PASSWORD, SECRET_KEY, INFLUX_TOKEN

# 4. Build & start services
docker compose -f docker-compose.prod.yml up -d --build

# 5. ติดตั้ง firmware
cd firmware
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp ../.env .env
sed -i 's/MQTT_BROKER=mosquitto/MQTT_BROKER=localhost/' .env

# 6. Start firmware (เมื่อ hardware พร้อม)
sudo cp ../deploy/airguard-firmware.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable airguard-firmware
sudo systemctl start airguard-firmware
```

### คำสั่งที่ใช้บ่อยบน Pi

```bash
# ดู status
sudo systemctl status airguard-firmware
docker compose -f docker-compose.prod.yml ps

# ดู logs
journalctl -u airguard-firmware -f
docker compose -f docker-compose.prod.yml logs -f backend

# รีสตาร์ท
sudo systemctl restart airguard-firmware
docker compose -f docker-compose.prod.yml restart

# อัปเดต
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 📊 มาตรฐาน AQI ไทย

ระบบใช้มาตรฐาน **กรมควบคุมมลพิษ (PCD) ประกาศ พ.ศ. 2566**

| ระดับ | AQI | PM2.5 (µg/m³) | ความหมาย | สีแสดง | ความเร็วพัดลม |
|------|-----|---------------|---------|--------|-------------|
| 1 | 0–25 | 0–15.0 | 🟢 ดีมาก | เขียว | 20% |
| 2 | 26–50 | 15.1–25.0 | 🟡 ดี | เหลือง | 40% |
| 3 | 51–100 | 25.1–37.5 | 🟠 ปานกลาง | ส้ม | 60% |
| 4 | 101–200 | 37.6–75.0 | 🔴 มีผลต่อสุขภาพ | แดง | 80% |
| 5 | >200 | >75.0 | 🟣 อันตราย | ม่วง | 100% |

> ค่ามาตรฐาน 24-ชั่วโมง: **37.5 µg/m³** | รายปี: **15 µg/m³**

---

## 🤖 AI / Machine Learning

### LSTM PM2.5 Forecast

| รายละเอียด | ค่า |
|-----------|-----|
| Architecture | LSTM (2 layers) → Dense |
| Input | 24 timesteps × 1 feature (PM2.5) |
| Output | PM2.5 ล่วงหน้า 1 ชั่วโมง |
| Training data | Synthetic 30 วัน (8,640 samples) |
| Val Loss (MSE) | 0.0103 |
| Best Epoch | 38 / 50 (EarlyStopping) |
| FP32 TFLite | 139 KB |
| INT8 TFLite | 60 KB (Dynamic Range Quantization) |

### Model Files

```
ml/models/
├── pm25_lstm.keras          ← Keras full model (train/fine-tune)
├── best_lstm.keras          ← Best checkpoint
├── pm25_lstm.tflite         ← Inference บน Pi (FP32)
├── pm25_lstm_int8.tflite    ← Inference บน Pi (INT8, เร็วกว่า ~2×)
└── model_meta.json          ← Scaler min/max + model metadata
```

> **หมายเหตุ:** TFLite ใช้ `SELECT_TF_OPS` (Flex Delegate) เนื่องจาก LSTM ใช้ TensorList ops  
> ต้องใช้ `tflite-runtime` พร้อม Flex Delegate บน Pi (`pip install tflite-runtime`)

### AI Chat (Local LLM)

ใช้ **Ollama** + **Phi-3 Mini** ทำงานบน Pi โดยไม่ต้องต่อ internet:
```bash
# ติดตั้ง Ollama บน Pi
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull phi3:mini
```

---

## 📡 API Reference

Base URL: `http://pi-ip:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login → JWT token |
| `POST` | `/api/auth/register` | สมัครสมาชิก |
| `GET` | `/api/sensor/latest` | ค่าล่าสุดจาก sensor |
| `GET` | `/api/sensor/history?hours=24` | ประวัติข้อมูล |
| `GET` | `/api/fan/speed` | ความเร็วพัดลมปัจจุบัน |
| `POST` | `/api/fan/speed` | ตั้งค่าความเร็วพัดลม |
| `GET` | `/api/alerts/rules` | ดู alert rules |
| `POST` | `/api/alerts/rules` | สร้าง alert rule |
| `POST` | `/api/ai/predict` | พยากรณ์ PM2.5 (LSTM) |
| `POST` | `/api/ai/chat` | AI Chat (Ollama) |
| `WS` | `/ws/{device_id}` | WebSocket real-time stream |

> Swagger UI: `http://pi-ip:8000/docs`

---

## 📚 อ้างอิง

1. กรมควบคุมมลพิษ. (2566). **ประกาศคณะกรรมการสิ่งแวดล้อมแห่งชาติ ฉบับที่ 36 (พ.ศ. 2553) — มาตรฐานคุณภาพอากาศในบรรยากาศโดยทั่วไป**. air4thai.pcd.go.th

2. World Health Organization. (2021). **WHO Global Air Quality Guidelines: Particulate Matter (PM2.5 and PM10), Ozone, Nitrogen Dioxide, Sulfur Dioxide and Carbon Monoxide**. WHO Press.

3. Tiangolo, S. (2023). **FastAPI Documentation**. fastapi.tiangolo.com

4. InfluxData. (2024). **InfluxDB 2.x Documentation**. docs.influxdata.com

5. Hochreiter, S., & Schmidhuber, J. (1997). **Long Short-Term Memory**. Neural Computation, 9(8), 1735–1780.

6. TensorFlow Team. (2024). **TensorFlow Lite Guide**. tensorflow.org/lite

7. Raspberry Pi Foundation. (2024). **Raspberry Pi Documentation**. raspberrypi.com/documentation

---

<div align="center">

**AirGuard Pi v1.0** · Thai PCD PM2.5 Standard · Raspberry Pi 4  
Built with ❤️ for IoT Senior Project

</div>
#   P r o j c e t _ I O T  
 