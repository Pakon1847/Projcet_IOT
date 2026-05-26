"""
AirGuard Pi — Main Entry Point
firmware/main.py

รันตรง  :  python main.py
systemd  :  sudo systemctl start airguard

สถาปัตยกรรม
-----------
  Thread-1  SensorLoop     อ่าน PMS5003 + BME280 → publish MQTT
  Thread-2  FanController  subscribe MQTT → ปรับ PWM (GPIO18)
  Thread-3  OLEDDisplay    subscribe MQTT → อัปเดต SSD1306
  Watchdog  ตรวจ thread ทุก 30 วินาที + CPU temp
"""

import os
import sys
import json
import time
import signal
import logging
import logging.handlers          # ← ต้อง import ก่อน basicConfig
import threading
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from config import Config
from utils.aqi_local import calculate_thai_aqi

# ── Logging setup ──────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            _LOG_DIR / "airguard.log",
            maxBytes=5 * 1024 * 1024,   # 5 MB
            backupCount=3,
        ),
    ],
)
logger = logging.getLogger("airguard.main")

VERSION = "1.0.0"


def _banner():
    print(f"""
╔══════════════════════════════════════╗
║    AirGuard Pi  v{VERSION}              ║
║  PM2.5 Smart Air Purifier System    ║
║  Thai PCD Standard (PCD 2566)       ║
╚══════════════════════════════════════╝
Device  : {Config().DEVICE_ID}
Broker  : {Config().MQTT_BROKER}:{Config().MQTT_PORT}
Interval: {Config().SENSOR_INTERVAL} s
""")


# ══════════════════════════════════════════════════════════════════════════════
# Thread-1 : SensorLoop
# ══════════════════════════════════════════════════════════════════════════════

class SensorLoop(threading.Thread):
    """อ่าน PMS5003 + BME280 ทุก interval วินาที แล้ว publish MQTT"""

    def __init__(self, config: Config, stop: threading.Event):
        super().__init__(name="SensorLoop", daemon=True)
        self.cfg        = config
        self.stop       = stop
        self._last_ok   = 0.0     # timestamp ของ reading สำเร็จล่าสุด
        self._pms       = None
        self._bme       = None
        self._client    = None

    # ── health check (เรียกจาก watchdog) ─────────────────────────────────
    @property
    def healthy(self) -> bool:
        return time.time() - self._last_ok < self.cfg.SENSOR_INTERVAL * 3

    # ── setup ─────────────────────────────────────────────────────────────
    def _init_hardware(self):
        from sensor_reader import PMS5003, BME280Sensor
        self._pms = PMS5003(port=self.cfg.PMS5003_PORT)
        self._bme = BME280Sensor()
        logger.info("Hardware ready: PMS5003 + BME280")

    def _init_mqtt(self):
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=f"sensor_{self.cfg.DEVICE_ID}",
        )
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.connect(self.cfg.MQTT_BROKER, self.cfg.MQTT_PORT, keepalive=60)
        self._client.loop_start()

    def _on_connect(self, client, userdata, flags, rc, props=None):
        if rc == 0:
            logger.info("SensorLoop MQTT connected")
        else:
            logger.error(f"SensorLoop MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, flags, rc=None, props=None):
        logger.warning(f"SensorLoop MQTT disconnected rc={rc}")

    # ── read + publish ─────────────────────────────────────────────────────
    def _read_publish(self):
        pms = self._pms.read()
        if pms is None:
            raise RuntimeError("PMS5003 returned None — ตรวจสาย UART")

        bme  = self._bme.read()
        pm25 = float(pms["pm2_5"])
        aqi  = calculate_thai_aqi(pm25)

        payload = {
            "device_id":   self.cfg.DEVICE_ID,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "pm1_0":       pms["pm1_0"],
            "pm2_5":       pm25,
            "pm10":        pms["pm10"],
            "temperature": bme["temperature"],
            "humidity":    bme["humidity"],
            "pressure":    bme["pressure"],
            "aqi":         aqi.aqi,
            "aqi_level":   aqi.level,
            "fan_speed":   aqi.fan_speed_pct,
        }

        self._client.publish(
            f"pm25/sensor/{self.cfg.DEVICE_ID}",
            json.dumps(payload),
            qos=1,
            retain=True,
        )

        logger.info(
            f"PM2.5={pm25:.1f} µg/m³  AQI={aqi.aqi} [{aqi.level}]  "
            f"Temp={bme['temperature']:.1f}°C  Hum={bme['humidity']:.0f}%  "
            f"Fan-rec={aqi.fan_speed_pct}%"
        )
        self._last_ok = time.time()

    # ── main loop ──────────────────────────────────────────────────────────
    def run(self):
        logger.info("SensorLoop starting...")

        # retry init (hardware อาจยังไม่พร้อมตอน boot)
        for attempt in range(1, 6):
            try:
                self._init_hardware()
                self._init_mqtt()
                break
            except Exception as e:
                logger.error(f"Init attempt {attempt}/5 failed: {e}")
                if attempt == 5:
                    logger.critical("SensorLoop: ไม่สามารถเริ่ม hardware ได้")
                    return
                self.stop.wait(5)

        while not self.stop.is_set():
            try:
                self._read_publish()
            except Exception as e:
                logger.error(f"SensorLoop error: {e}")
            self.stop.wait(self.cfg.SENSOR_INTERVAL)

        # cleanup
        try:
            self._pms and self._pms.close()
            self._client and self._client.loop_stop()
        except Exception:
            pass
        logger.info("SensorLoop stopped")


# ══════════════════════════════════════════════════════════════════════════════
# Thread-2 : FanController wrapper
# ══════════════════════════════════════════════════════════════════════════════

def _start_fan_thread(stop: threading.Event) -> threading.Thread:
    """
    FanController มี run() loop ของตัวเอง
    Wrap ใน daemon thread — cleanup เมื่อ stop_event set
    """
    from fan_controller import FanController

    fc = FanController()

    def _body():
        try:
            fc.run()
        except Exception as e:
            logger.error(f"FanController error: {e}")
        finally:
            try:
                fc.stop()
                fc.cleanup()
            except Exception:
                pass
            logger.info("FanController stopped")

    t = threading.Thread(target=_body, name="FanController", daemon=True)
    t.start()
    logger.info("Thread started: FanController")
    return t


# ══════════════════════════════════════════════════════════════════════════════
# Thread-3 : OLEDDisplay wrapper
# ══════════════════════════════════════════════════════════════════════════════

def _start_oled_thread(stop: threading.Event) -> threading.Thread:
    """OLEDDisplay มี run() loop ของตัวเอง"""
    from oled_display import OLEDDisplay

    oled = OLEDDisplay()

    def _body():
        try:
            oled.run()
        except Exception as e:
            logger.error(f"OLEDDisplay error: {e}")
        logger.info("OLEDDisplay stopped")

    t = threading.Thread(target=_body, name="OLEDDisplay", daemon=True)
    t.start()
    logger.info("Thread started: OLEDDisplay")
    return t


# ══════════════════════════════════════════════════════════════════════════════
# Watchdog
# ══════════════════════════════════════════════════════════════════════════════

def _watchdog(
    threads: list[threading.Thread],
    sensor: SensorLoop,
    stop: threading.Event,
):
    logger.info("Watchdog started (interval=30s)")
    while not stop.wait(30):
        alive = [t.name for t in threads if t.is_alive()]
        dead  = [t.name for t in threads if not t.is_alive()]

        if dead:
            logger.error(f"Dead threads: {dead}")
        if not sensor.healthy:
            logger.warning("SensorLoop: ไม่ได้รับข้อมูลนาน > 3 รอบ")

        # CPU temperature
        try:
            raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text()
            cpu = int(raw.strip()) / 1000
            msg = f"CPU temp={cpu:.1f}°C  Alive={alive}"
            if cpu > 80:
                logger.warning(f"CPU temp สูง! {msg}")
            else:
                logger.debug(msg)
        except FileNotFoundError:
            pass   # ไม่ได้รันบน Pi จริง

    logger.info("Watchdog stopped")


# ══════════════════════════════════════════════════════════════════════════════
# Pre-flight check
# ══════════════════════════════════════════════════════════════════════════════

def _check_packages() -> bool:
    """ตรวจ package ที่จำเป็น ก่อน import hardware"""
    required = {
        "RPi.GPIO":              "RPi.GPIO",
        "serial":                "pyserial",
        "board":                 "adafruit-blinka",
        "adafruit_bme280":       "adafruit-circuitpython-bme280",
        "adafruit_ssd1306":      "adafruit-circuitpython-ssd1306",
        "paho.mqtt":             "paho-mqtt",
        "PIL":                   "Pillow",
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        logger.critical(f"ขาด package: {missing}")
        logger.critical("แก้ไข: pip install -r requirements.txt")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    _banner()

    if not _check_packages():
        sys.exit(1)

    if os.geteuid() != 0:
        logger.warning(
            "ไม่ได้รันเป็น root — "
            "ถ้า GPIO/UART ใช้ไม่ได้ให้รัน: sudo python main.py  "
            "หรือเพิ่ม user เข้า group gpio และ dialout"
        )

    cfg        = Config()
    stop_event = threading.Event()
    threads: list[threading.Thread] = []

    # ── signal handlers ────────────────────────────────────────────────────
    def _handle_signal(sig, _frame):
        logger.info(f"รับ signal {signal.Signals(sig).name} — กำลัง shutdown")
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    # ── start threads ───────────────────────────────────────────────────────
    sensor = SensorLoop(cfg, stop_event)
    sensor.start()
    threads.append(sensor)

    time.sleep(2)   # ให้ sensor connect ก่อน fan + oled subscribe

    try:
        threads.append(_start_fan_thread(stop_event))
    except Exception as e:
        logger.error(f"ไม่สามารถเริ่ม FanController: {e}")

    try:
        threads.append(_start_oled_thread(stop_event))
    except Exception as e:
        logger.error(f"ไม่สามารถเริ่ม OLEDDisplay: {e}")

    # ── watchdog ────────────────────────────────────────────────────────────
    wd = threading.Thread(
        target=_watchdog,
        args=(threads, sensor, stop_event),
        name="Watchdog",
        daemon=True,
    )
    wd.start()

    logger.info("ระบบทำงานปกติ — กด Ctrl+C หรือ systemctl stop airguard เพื่อหยุด")

    # ── wait ────────────────────────────────────────────────────────────────
    stop_event.wait()

    logger.info("กำลังหยุดทุก thread (รอสูงสุด 10s)...")
    for t in threads:
        t.join(timeout=10)
        if t.is_alive():
            logger.warning(f"Thread {t.name} ไม่หยุดใน 10s")

    logger.info("AirGuard Pi หยุดทำงานแล้ว 👋")


if __name__ == "__main__":
    main()
