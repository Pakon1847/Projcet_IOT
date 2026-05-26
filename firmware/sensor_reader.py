"""
PM2.5 Sensor Reader — Raspberry Pi 4
รองรับ: PMS5003 (UART) + BME280 (I2C)
เก็บข้อมูลทุก 10 วินาที ส่งผ่าน MQTT

วิธีเชื่อมต่อ:
  PMS5003: VCC→5V, GND→GND, TX→GPIO15(RXD), RX→GPIO14(TXD)
  BME280 : VCC→3.3V, GND→GND, SDA→GPIO2, SCL→GPIO3
"""

import time
import json
import logging
import serial
import struct
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import board
import busio
import adafruit_bme280.basic as adafruit_bme280

from config import Config
from utils.aqi_local import calculate_thai_aqi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class PMS5003:
    """Driver สำหรับ PMS5003 PM2.5 Sensor (UART)"""

    START_BYTE_1 = 0x42
    START_BYTE_2 = 0x4D
    FRAME_LENGTH = 32

    def __init__(self, port: str = "/dev/ttyS0", baudrate: int = 9600):
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=2)
        logger.info(f"PMS5003 connected on {port}")

    def read(self) -> dict | None:
        """อ่านค่า PM2.5, PM10 จาก sensor"""
        data = self.serial.read(self.FRAME_LENGTH)
        if len(data) != self.FRAME_LENGTH:
            return None
        if data[0] != self.START_BYTE_1 or data[1] != self.START_BYTE_2:
            return None

        # Parse frame (big-endian unsigned shorts)
        frame = struct.unpack(">HHHHHHHHHHHHHH", data[4:32])
        return {
            "pm1_0":  frame[0],   # PM1.0 (µg/m³) — Corrected
            "pm2_5":  frame[1],   # PM2.5 (µg/m³) — Corrected  ← ค่าหลัก
            "pm10":   frame[2],   # PM10  (µg/m³) — Corrected
            "pm1_0_atm":  frame[3],
            "pm2_5_atm":  frame[4],
            "pm10_atm":   frame[5],
        }

    def close(self):
        self.serial.close()


class BME280Sensor:
    """Driver สำหรับ BME280 Temperature/Humidity/Pressure (I2C)"""

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)
        self.sensor.sea_level_pressure = 1013.25
        logger.info("BME280 connected on I2C")

    def read(self) -> dict:
        return {
            "temperature": round(self.sensor.temperature, 1),
            "humidity":    round(self.sensor.relative_humidity, 1),
            "pressure":    round(self.sensor.pressure, 1),
        }


class SensorPublisher:
    """รวม sensor readings แล้วส่งผ่าน MQTT"""

    def __init__(self):
        self.config = Config()
        self.pms = PMS5003(port=self.config.PMS5003_PORT)
        self.bme = BME280Sensor()
        self._setup_mqtt()

    def _setup_mqtt(self):
        self.client = mqtt.Client(client_id=f"firmware_{self.config.DEVICE_ID}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(self.config.MQTT_BROKER, self.config.MQTT_PORT, keepalive=60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"MQTT connected to {self.config.MQTT_BROKER}:{self.config.MQTT_PORT}")
        else:
            logger.error(f"MQTT connection failed: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"MQTT disconnected (rc={rc}), reconnecting...")

    def publish(self, payload: dict):
        topic = f"pm25/sensor/{self.config.DEVICE_ID}"
        self.client.publish(topic, json.dumps(payload), qos=1)

    def run(self, interval_sec: int = 10):
        """Main loop — อ่าน sensor ทุก interval_sec วินาที"""
        logger.info(f"Starting sensor reader (interval={interval_sec}s)")
        while True:
            try:
                pms_data = self.pms.read()
                bme_data = self.bme.read()

                if pms_data is None:
                    logger.warning("PMS5003 read failed, skipping...")
                    time.sleep(interval_sec)
                    continue

                pm25 = pms_data["pm2_5"]
                aqi = calculate_thai_aqi(pm25)

                payload = {
                    "device_id":   self.config.DEVICE_ID,
                    "timestamp":   datetime.now(timezone.utc).isoformat(),
                    "pm1_0":       pms_data["pm1_0"],
                    "pm2_5":       pm25,
                    "pm10":        pms_data["pm10"],
                    "temperature": bme_data["temperature"],
                    "humidity":    bme_data["humidity"],
                    "pressure":    bme_data["pressure"],
                    "aqi":         aqi["aqi"],
                    "aqi_level":   aqi["level"],
                }

                self.publish(payload)
                logger.info(
                    f"PM2.5={pm25} µg/m³ | AQI={aqi['aqi']} ({aqi['level']}) "
                    f"| Temp={bme_data['temperature']}°C | Hum={bme_data['humidity']}%"
                )

            except Exception as e:
                logger.error(f"Sensor read error: {e}")

            time.sleep(interval_sec)


if __name__ == "__main__":
    publisher = SensorPublisher()
    publisher.run(interval_sec=10)
