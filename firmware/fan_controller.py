"""
Fan Controller — Raspberry Pi 4
ควบคุมความเร็วพัดลม 12V ผ่าน MOSFET IRF520 ด้วย PWM hardware

วงจร:
  GPIO18 (PWM0) → 1kΩ → Gate
  Source → GND (common กับ Pi และ 12V PSU)
  Drain → Fan (−)
  Fan (+) → 12V PSU (+)

MQTT topics (subscribe):
  pm25/fan/{device_id}/set      — payload: {"speed": 0-100, "mode": "manual"|"auto"}
  pm25/sensor/{device_id}       — payload sensor: ใช้ตัดสินใจ auto mode

MQTT topics (publish):
  pm25/fan/{device_id}/status   — payload: {"speed": int, "mode": str, "rpm_est": int}
"""

import time
import json
import logging
import threading

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

from config import Config
from utils.aqi_local import calculate_thai_aqi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PWM_FREQ = 25_000  # Hz — 25 kHz เพื่อไม่ให้ได้ยินเสียง coil whine


class FanController:
    """
    ควบคุมพัดลม 12V ผ่าน MOSFET IRF520 บน GPIO18 (PWM0)
    รองรับ 2 โหมด:
      auto   — ปรับความเร็วตาม AQI จาก MQTT sensor topic
      manual — ผู้ใช้ตั้งค่าโดยตรงผ่าน API / MQTT
    """

    MIN_SPEED = 0    # % (0 = หยุด)
    MAX_SPEED = 100  # %
    MIN_RUN   = 20   # % ความเร็วต่ำสุดเมื่อเปิดพัดลม (ต่ำกว่าพัดลมอาจไม่หมุน)

    def __init__(self):
        self.config = Config()
        self._speed  = 0       # % ปัจจุบัน
        self._mode   = "auto"  # "auto" | "manual"
        self._lock   = threading.Lock()
        self._pwm: GPIO.PWM | None = None
        self._setup_gpio()
        self._setup_mqtt()

    # ── GPIO ──────────────────────────────────────────────────────────────

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.config.FAN_GPIO_PIN, GPIO.OUT)
        self._pwm = GPIO.PWM(self.config.FAN_GPIO_PIN, PWM_FREQ)
        self._pwm.start(0)
        logger.info(f"PWM started on GPIO{self.config.FAN_GPIO_PIN} @ {PWM_FREQ} Hz")

    def _set_duty_cycle(self, speed_pct: int):
        """ตั้ง duty cycle — 0 = หยุด, 100 = เต็ม"""
        speed_pct = max(self.MIN_SPEED, min(self.MAX_SPEED, speed_pct))
        if self._pwm:
            self._pwm.ChangeDutyCycle(speed_pct)

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def speed(self) -> int:
        return self._speed

    @property
    def mode(self) -> str:
        return self._mode

    def set_speed(self, speed_pct: int, mode: str = "manual"):
        """ตั้งความเร็วพัดลม (เรียกจากภายนอกหรือ auto loop)"""
        with self._lock:
            speed_pct = max(self.MIN_SPEED, min(self.MAX_SPEED, int(speed_pct)))
            # ถ้าไม่ใช่ 0 แต่ต่ำกว่า MIN_RUN ให้ปัดขึ้น
            if 0 < speed_pct < self.MIN_RUN:
                speed_pct = self.MIN_RUN
            self._speed = speed_pct
            self._mode  = mode
            self._set_duty_cycle(speed_pct)
            logger.info(f"Fan speed → {speed_pct}% [{mode}]")

    def set_mode(self, mode: str):
        """สลับ auto/manual"""
        if mode in ("auto", "manual"):
            self._mode = mode
            logger.info(f"Fan mode → {mode}")

    def stop(self):
        """หยุดพัดลม"""
        self.set_speed(0, "manual")

    def cleanup(self):
        """เรียกก่อนปิด process"""
        if self._pwm:
            self._pwm.stop()
        GPIO.cleanup()
        logger.info("GPIO cleaned up")

    # ── MQTT ──────────────────────────────────────────────────────────────

    def _setup_mqtt(self):
        self.client = mqtt.Client(
            client_id=f"fan_{self.config.DEVICE_ID}"
        )
        self.client.on_connect    = self._on_connect
        self.client.on_message    = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(self.config.MQTT_BROKER, self.config.MQTT_PORT, keepalive=60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT connected")
            # Subscribe: คำสั่งตั้งค่าพัดลม
            client.subscribe(f"pm25/fan/{self.config.DEVICE_ID}/set", qos=1)
            # Subscribe: ข้อมูล sensor สำหรับ auto mode
            client.subscribe(f"pm25/sensor/{self.config.DEVICE_ID}", qos=0)
        else:
            logger.error(f"MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"MQTT disconnected rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic   = msg.topic

            # คำสั่งตั้งค่าพัดลมโดยตรง
            if topic.endswith("/set"):
                speed = int(payload.get("speed", self._speed))
                mode  = payload.get("mode", "manual")
                self.set_speed(speed, mode)
                self._publish_status()

            # ข้อมูล sensor — ใช้เฉพาะเมื่อ auto mode
            elif "pm2_5" in payload:
                if self._mode == "auto":
                    pm25 = float(payload["pm2_5"])
                    aqi_result = calculate_thai_aqi(pm25)
                    self.set_speed(aqi_result.fan_speed_pct, "auto")
                    self._publish_status()

        except Exception as e:
            logger.error(f"Message handling error: {e}")

    def _publish_status(self):
        topic = f"pm25/fan/{self.config.DEVICE_ID}/status"
        payload = {
            "speed":    self._speed,
            "mode":     self._mode,
            "rpm_est":  int(self._speed * 15),  # ประมาณ 1500 RPM ที่ 100%
        }
        self.client.publish(topic, json.dumps(payload), qos=0)

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        """ค้างไว้จนกว่าจะ Ctrl+C"""
        logger.info(f"Fan controller running (mode={self._mode})")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down fan controller...")
        finally:
            self.stop()
            self.cleanup()


if __name__ == "__main__":
    controller = FanController()
    controller.run()
