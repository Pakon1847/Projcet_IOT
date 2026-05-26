"""
OLED Display Driver — SSD1306 128x64 (I2C)
แสดงข้อมูล PM2.5 / AQI / Temp / Humidity / Fan speed

วงจร:
  VCC → Pin 17 (3.3V)
  GND → Pin 14
  SDA → Pin 3 (GPIO2)
  SCL → Pin 5 (GPIO3)
  I2C Address: 0x3C

Layout หน้าจอ (128×64 px):
  ┌─────────────────────────┐
  │ AirGuard Pi  [●] ปานกลาง│  row 0  (header)
  ├─────────────────────────┤
  │  PM2.5   28.4 µg/m³    │  row 1  (big value)
  │  AQI     78             │  row 2
  ├─────────────────────────┤
  │  Temp 27.3°C  Hum 68%  │  row 3
  │  Fan  60%   Auto        │  row 4
  └─────────────────────────┘

MQTT topics (subscribe):
  pm25/sensor/{device_id}       — ข้อมูล sensor
  pm25/fan/{device_id}/status   — ข้อมูลพัดลม
"""

import time
import json
import logging
import threading
from datetime import datetime

import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import paho.mqtt.client as mqtt

from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── AQI level → short label ───────────────────────────────────────────────
AQI_SHORT = {
    "ดีมาก":              "VERY GOOD",
    "ดี":                 "GOOD",
    "ปานกลาง":            "MODERATE",
    "เริ่มมีผลต่อสุขภาพ": "UNHEALTHY*",
    "มีผลต่อสุขภาพ":      "UNHEALTHY",
}


class OLEDDisplay:
    """
    จัดการ SSD1306 128×64 — อัปเดตหน้าจอทุกครั้งที่ได้ข้อมูลใหม่จาก MQTT
    """

    WIDTH  = 128
    HEIGHT = 64

    def __init__(self):
        self.config = Config()
        self._data: dict = {
            "pm2_5":       "--",
            "aqi":         "--",
            "aqi_level":   "รอข้อมูล...",
            "temperature": "--",
            "humidity":    "--",
            "fan_speed":   "--",
            "fan_mode":    "--",
        }
        self._lock = threading.Lock()
        self._setup_display()
        self._setup_fonts()
        self._setup_mqtt()
        self._draw_splash()

    # ── Hardware setup ────────────────────────────────────────────────────

    def _setup_display(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.oled = adafruit_ssd1306.SSD1306_I2C(
            self.WIDTH, self.HEIGHT, i2c, addr=0x3C
        )
        self.oled.fill(0)
        self.oled.show()
        logger.info("OLED SSD1306 initialized (128x64, I2C 0x3C)")

    def _setup_fonts(self):
        try:
            # ถ้ามี font ที่กว้างกว่าให้ใช้
            self.font_large  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
            self.font_small  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
        except (OSError, IOError):
            # Fallback: default bitmap font
            self.font_large  = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small  = ImageFont.load_default()
            logger.warning("TrueType font not found — using default bitmap font")

    # ── Drawing ───────────────────────────────────────────────────────────

    def _draw_splash(self):
        """Splash screen ตอน boot"""
        image = Image.new("1", (self.WIDTH, self.HEIGHT))
        draw  = ImageDraw.Draw(image)
        draw.text((10, 18), "AirGuard Pi", font=self.font_medium, fill=255)
        draw.text((18, 34), "PM2.5 Monitor", font=self.font_small, fill=255)
        draw.text((30, 50), "กรมควบคุมมลพิษ", font=self.font_small, fill=255)
        self._show(image)
        time.sleep(2)

    def _draw_main(self):
        """วาดหน้าจอหลัก"""
        with self._lock:
            d = dict(self._data)

        image = Image.new("1", (self.WIDTH, self.HEIGHT))
        draw  = ImageDraw.Draw(image)

        # ── Row 0: Header bar ──────────────────────────────────────────
        draw.rectangle((0, 0, self.WIDTH, 12), fill=255)
        level_short = AQI_SHORT.get(d["aqi_level"], d["aqi_level"][:10])
        header = f"PM2.5 | {level_short}"
        draw.text((2, 2), header, font=self.font_small, fill=0)
        # dot indicator (right)
        draw.ellipse((119, 3, 126, 10), fill=0)

        # ── Row 1: PM2.5 big value ────────────────────────────────────
        pm_str = f"{d['pm2_5']}"
        draw.text((2, 15), pm_str, font=self.font_large, fill=255)
        draw.text((52, 22), "ug/m3", font=self.font_small, fill=255)

        # ── Row 2: AQI ───────────────────────────────────────────────
        draw.text((2, 36), f"AQI {d['aqi']}", font=self.font_medium, fill=255)

        # ── Divider ───────────────────────────────────────────────────
        draw.line((0, 48, self.WIDTH, 48), fill=255)

        # ── Row 3: Temp + Humidity ────────────────────────────────────
        draw.text((2, 50), f"{d['temperature']}C  {d['humidity']}%", font=self.font_small, fill=255)

        # ── Row 4: Fan ───────────────────────────────────────────────
        draw.text((75, 50), f"Fan:{d['fan_speed']}%", font=self.font_small, fill=255)

        # ── Clock (bottom right) ──────────────────────────────────────
        now = datetime.now().strftime("%H:%M")
        draw.text((100, 56), now, font=self.font_small, fill=255)

        self._show(image)

    def _show(self, image: Image.Image):
        self.oled.image(image)
        self.oled.show()

    # ── MQTT ──────────────────────────────────────────────────────────────

    def _setup_mqtt(self):
        self.client = mqtt.Client(client_id=f"oled_{self.config.DEVICE_ID}")
        self.client.on_connect    = self._on_connect
        self.client.on_message    = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(self.config.MQTT_BROKER, self.config.MQTT_PORT, keepalive=60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("OLED MQTT connected")
            client.subscribe(f"pm25/sensor/{self.config.DEVICE_ID}", qos=0)
            client.subscribe(f"pm25/fan/{self.config.DEVICE_ID}/status", qos=0)
        else:
            logger.error(f"OLED MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"OLED MQTT disconnected rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            with self._lock:
                if "pm2_5" in payload:
                    self._data["pm2_5"]       = round(payload["pm2_5"], 1)
                    self._data["aqi"]         = payload.get("aqi", "--")
                    self._data["aqi_level"]   = payload.get("aqi_level", "--")
                    self._data["temperature"] = payload.get("temperature", "--")
                    self._data["humidity"]    = payload.get("humidity", "--")
                if "speed" in payload:
                    self._data["fan_speed"] = payload["speed"]
                    self._data["fan_mode"]  = payload.get("mode", "--")
            self._draw_main()
        except Exception as e:
            logger.error(f"OLED message error: {e}")

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        """วนลูป refresh หน้าจอทุก 10 วินาที (เผื่อ MQTT ไม่มาข้อมูล)"""
        logger.info("OLED display running")
        try:
            while True:
                self._draw_main()
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("OLED shutting down")
        finally:
            self.oled.fill(0)
            self.oled.show()


if __name__ == "__main__":
    display = OLEDDisplay()
    display.run()
