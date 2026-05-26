"""
Mock Sensor Script — ทดสอบ pipeline บน PC (ไม่ต้องมี Pi หรือ hardware จริง)
จำลอง PMS5003 + BME280 → ส่งผ่าน MQTT เหมือน firmware จริงทุกอย่าง

วิธีใช้:
  pip install paho-mqtt python-dotenv
  python mock_sensor.py                        # normal mode
  python mock_sensor.py --scenario spike       # จำลองค่าพุ่งสูง
  python mock_sensor.py --scenario pollution   # จำลองอากาศแย่ต่อเนื่อง
  python mock_sensor.py --scenario clean       # จำลองอากาศดีมาก
  python mock_sensor.py --scenario full        # วนทุก scenario อัตโนมัติ
  python mock_sensor.py --interval 2           # ส่งทุก 2 วินาที (default 10)
  python mock_sensor.py --device my_pi_002     # กำหนด device_id เอง
"""

import argparse
import json
import math
import random
import signal
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field

import paho.mqtt.client as mqtt

# ── Config ────────────────────────────────────────────────────────────────────

MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
DEVICE_ID     = "pi4_home_001"
INTERVAL_SEC  = 10

# Thai AQI breakpoints (PCD 2566) — ใช้คำนวณ AQI จาก PM2.5
_BREAKPOINTS = [
    (0.0,  15.0,   0,  25, "ดีมาก"),
    (15.1, 25.0,  26,  50, "ดี"),
    (25.1, 37.5,  51, 100, "ปานกลาง"),
    (37.6, 75.0, 101, 200, "เริ่มมีผลต่อสุขภาพ"),
    (75.1, 999., 201, 500, "มีผลต่อสุขภาพ"),
]


def pm25_to_aqi(pm25: float) -> tuple[int, str]:
    pm25 = max(0.0, pm25)
    for c_lo, c_hi, a_lo, a_hi, level in _BREAKPOINTS:
        if pm25 <= c_hi:
            aqi = a_lo + (pm25 - c_lo) / (c_hi - c_lo) * (a_hi - a_lo)
            return int(round(aqi)), level
    return 500, "มีผลต่อสุขภาพ"


# ── Scenarios ─────────────────────────────────────────────────────────────────

@dataclass
class Scenario:
    name:        str
    description: str
    pm25_base:   float          # ค่ากลาง PM2.5
    pm25_noise:  float = 3.0    # noise +/-
    pm25_wave:   float = 5.0    # amplitude คลื่น sine
    temp_base:   float = 27.0
    hum_base:    float = 65.0
    color:       str   = "\033[0m"

SCENARIOS: dict[str, Scenario] = {
    "clean": Scenario(
        name="clean", description="อากาศดีมาก (< 15 µg/m³)",
        pm25_base=8.0, pm25_noise=2.0, pm25_wave=3.0,
        temp_base=25.0, hum_base=55.0, color="\033[96m",   # cyan
    ),
    "normal": Scenario(
        name="normal", description="อากาศปกติ (15-30 µg/m³) — day/night cycle",
        pm25_base=22.0, pm25_noise=4.0, pm25_wave=8.0,
        temp_base=28.0, hum_base=65.0, color="\033[92m",   # green
    ),
    "moderate": Scenario(
        name="moderate", description="ปานกลาง (25-37.5 µg/m³)",
        pm25_base=31.0, pm25_noise=4.0, pm25_wave=6.0,
        temp_base=29.0, hum_base=70.0, color="\033[93m",   # yellow
    ),
    "spike": Scenario(
        name="spike", description="จำลองค่าพุ่งสูงเกินมาตรฐาน PCD แล้วกลับมา",
        pm25_base=25.0, pm25_noise=3.0, pm25_wave=30.0,
        temp_base=30.0, hum_base=72.0, color="\033[91m",   # red
    ),
    "pollution": Scenario(
        name="pollution", description="อากาศแย่ต่อเนื่อง (> 50 µg/m³)",
        pm25_base=60.0, pm25_noise=8.0, pm25_wave=10.0,
        temp_base=32.0, hum_base=80.0, color="\033[31m",   # dark red
    ),
}


# ── Data Generator ────────────────────────────────────────────────────────────

class SensorSimulator:
    """จำลองค่า sensor แบบสมจริง — มี noise + sine wave + day/night pattern"""

    def __init__(self, scenario: Scenario, device_id: str):
        self.scenario  = scenario
        self.device_id = device_id
        self._t        = 0.0   # เวลา (หน่วย: รอบการส่ง)

    def _day_factor(self) -> float:
        """
        จำลอง pattern กลางวัน/กลางคืน
        กลางวัน (peak ~14:00) = ค่าสูงกว่า
        กลางคืน (trough ~03:00) = ค่าต่ำกว่า
        """
        hour = datetime.now().hour + datetime.now().minute / 60
        # sine wave: peak ที่ 14:00, trough ที่ 02:00
        return 0.5 + 0.5 * math.sin((hour - 2) / 24 * 2 * math.pi)

    def read(self) -> dict:
        self._t += 1
        sc = self.scenario

        # PM2.5 = base + day_pattern*wave + sine(t)*wave/2 + noise
        day   = self._day_factor()
        wave  = sc.pm25_wave * math.sin(self._t * 0.3)
        noise = random.gauss(0, sc.pm25_noise)
        pm25  = max(0.0, sc.pm25_base + day * sc.pm25_wave * 0.5 + wave * 0.5 + noise)
        pm25  = round(pm25, 1)

        # PM10 ≈ PM2.5 * 1.4-1.8 (typical ratio)
        pm10  = round(pm25 * random.uniform(1.4, 1.8), 1)
        pm1_0 = round(pm25 * random.uniform(0.6, 0.85), 1)

        # Temperature — เปลี่ยนช้า
        temp_noise = random.gauss(0, 0.3)
        temp = round(sc.temp_base + day * 3.0 + temp_noise, 1)

        # Humidity — inverse กับอุณหภูมิเล็กน้อย
        hum_noise = random.gauss(0, 1.5)
        humidity  = round(max(20, min(95, sc.hum_base - day * 5 + hum_noise)), 1)

        # Pressure — เปลี่ยนน้อยมาก
        pressure = round(1013.25 + random.gauss(0, 0.5), 1)

        aqi, level = pm25_to_aqi(pm25)

        return {
            "device_id":   self.device_id,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "pm1_0":       pm1_0,
            "pm2_5":       pm25,
            "pm10":        pm10,
            "temperature": temp,
            "humidity":    humidity,
            "pressure":    pressure,
            "aqi":         aqi,
            "aqi_level":   level,
            "_mock":       True,
            "_scenario":   self.scenario.name,
        }


# ── Full auto scenario rotator ────────────────────────────────────────────────

FULL_ROTATION = [
    ("clean",      30),   # 30 รอบ
    ("normal",     40),
    ("moderate",   20),
    ("spike",      15),
    ("pollution",  20),
    ("moderate",   15),
    ("normal",     20),
]


# ── MQTT Publisher ────────────────────────────────────────────────────────────

class MockPublisher:
    def __init__(self, broker: str, port: int, device_id: str):
        self.broker    = broker
        self.port      = port
        self.device_id = device_id
        self.topic     = f"pm25/sensor/{device_id}"
        self._count    = 0
        self._client   = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"mock_{device_id}",
        )
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def connect(self):
        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            time.sleep(0.5)
        except ConnectionRefusedError:
            print(f"\n{RED}✗ ไม่สามารถเชื่อมต่อ MQTT ที่ {self.broker}:{self.port}{RESET}")
            print(f"  ตรวจสอบว่า Mosquitto กำลังทำงาน: {CYAN}docker compose up -d mosquitto{RESET}\n")
            sys.exit(1)

    def publish(self, payload: dict) -> bool:
        result = self._client.publish(self.topic, json.dumps(payload), qos=1)
        self._count += 1
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"{GREEN}✓ MQTT connected → {self.broker}:{self.port}{RESET}")
            print(f"  Publishing to: {CYAN}{self.topic}{RESET}\n")
        else:
            print(f"{RED}✗ MQTT connect failed rc={rc}{RESET}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            print(f"{YELLOW}⚠ MQTT disconnected rc={rc}{RESET}")

    @property
    def count(self) -> int:
        return self._count


# ── Terminal colors ───────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

AQI_COLORS = {
    "ดีมาก":              "\033[96m",   # cyan
    "ดี":                 "\033[92m",   # green
    "ปานกลาง":            "\033[93m",   # yellow
    "เริ่มมีผลต่อสุขภาพ": "\033[91m",   # red
    "มีผลต่อสุขภาพ":      "\033[31m",   # dark red
}


def print_reading(payload: dict, ok: bool, publisher: MockPublisher):
    pm25   = payload["pm2_5"]
    aqi    = payload["aqi"]
    level  = payload["aqi_level"]
    temp   = payload["temperature"]
    hum    = payload["humidity"]
    ts     = payload["timestamp"][11:19]   # HH:MM:SS only
    c      = AQI_COLORS.get(level, RESET)
    status = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    exceed = f"  {RED}⚠ เกินมาตรฐาน PCD 37.5!{RESET}" if pm25 > 37.5 else ""

    print(
        f"  {GRAY}[{ts}]{RESET} {status} "
        f"PM2.5={c}{BOLD}{pm25:5.1f}{RESET} µg/m³  "
        f"AQI={c}{aqi:3d}{RESET}  "
        f"{c}{level}{RESET}"
        f"  │  Temp={temp}°C  Hum={hum}%"
        f"  │  #{publisher.count}"
        f"{exceed}"
    )


def print_header(scenario: Scenario, interval: int, device_id: str):
    print(f"\n{'─'*70}")
    print(f"  {BOLD}AirGuard Pi — Mock Sensor{RESET}")
    print(f"  Device  : {CYAN}{device_id}{RESET}")
    print(f"  Scenario: {scenario.color}{BOLD}{scenario.name}{RESET}  {GRAY}({scenario.description}){RESET}")
    print(f"  Interval: {interval}s  │  มาตรฐาน PCD 2566: PM2.5 ≤ {YELLOW}37.5 µg/m³{RESET}")
    print(f"  Ctrl+C เพื่อหยุด")
    print(f"{'─'*70}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_scenario(scenario: Scenario, publisher: MockPublisher,
                 interval: int, rounds: int | None = None):
    """วน loop ส่งข้อมูล — rounds=None หมายถึงวนไม่หยุด"""
    sim = SensorSimulator(scenario, publisher.device_id)
    i   = 0
    while rounds is None or i < rounds:
        payload = sim.read()
        ok      = publisher.publish(payload)
        print_reading(payload, ok, publisher)
        time.sleep(interval)
        i += 1


def run_full(publisher: MockPublisher, interval: int):
    """วน scenario อัตโนมัติ ทดสอบ pipeline ทุกกรณี"""
    print(f"\n  {BOLD}Full rotation mode{RESET} — วน scenario อัตโนมัติ\n")
    rotation_num = 0
    while True:
        rotation_num += 1
        print(f"\n  {GRAY}── Rotation #{rotation_num} ─────────────────────────────{RESET}")
        for sc_name, rounds in FULL_ROTATION:
            sc = SCENARIOS[sc_name]
            print(f"\n  {sc.color}▶ Scenario: {sc_name}{RESET}  ({sc.description})  [{rounds} รอบ]")
            run_scenario(sc, publisher, interval, rounds=rounds)


def main():
    parser = argparse.ArgumentParser(description="Mock PM2.5 Sensor for pipeline testing")
    parser.add_argument("--scenario", "-s", default="normal",
                        choices=list(SCENARIOS.keys()) + ["full"],
                        help="Scenario ที่ต้องการจำลอง (default: normal)")
    parser.add_argument("--interval", "-i", type=int, default=INTERVAL_SEC,
                        help=f"ส่งข้อมูลทุก N วินาที (default: {INTERVAL_SEC})")
    parser.add_argument("--broker",   "-b", default=MQTT_BROKER,
                        help=f"MQTT broker (default: {MQTT_BROKER})")
    parser.add_argument("--port",     "-p", type=int, default=MQTT_PORT,
                        help=f"MQTT port (default: {MQTT_PORT})")
    parser.add_argument("--device",   "-d", default=DEVICE_ID,
                        help=f"Device ID (default: {DEVICE_ID})")
    args = parser.parse_args()

    publisher = MockPublisher(args.broker, args.port, args.device)
    publisher.connect()

    # Graceful shutdown on Ctrl+C
    def _shutdown(sig, frame):
        print(f"\n\n  {YELLOW}⏹ หยุด mock sensor (ส่งไปแล้ว {publisher.count} ครั้ง){RESET}\n")
        publisher.disconnect()
        sys.exit(0)
    signal.signal(signal.SIGINT, _shutdown)

    if args.scenario == "full":
        scenario = SCENARIOS["normal"]
        print_header(scenario, args.interval, args.device)
        run_full(publisher, args.interval)
    else:
        scenario = SCENARIOS[args.scenario]
        print_header(scenario, args.interval, args.device)
        run_scenario(scenario, publisher, args.interval)


if __name__ == "__main__":
    main()
