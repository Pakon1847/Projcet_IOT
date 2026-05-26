"""
MQTT Subscriber — รับข้อมูลจาก firmware แล้ว:
  1. บันทึกลง InfluxDB
  2. Broadcast ผ่าน WebSocket ไปยัง dashboard
  3. ตรวจ AlertRule และส่ง notification ถ้าเกิน threshold
"""

import json
import asyncio
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from app.config import settings
from app.services.influx import write_sensor_reading
from app.services.notification import notify
from app.ws.manager import ws_manager

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    global _loop
    _loop = loop


class MQTTSubscriber:
    """
    Subscribe ทุก topic pm25/sensor/# แล้วกระจายข้อมูล
    เรียก start() หลัง FastAPI app เริ่มทำงาน
    """

    def __init__(self):
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id="backend_subscriber",
        )
        self.client.on_connect    = self._on_connect
        self.client.on_message    = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def start(self):
        self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
        self.client.loop_start()
        logger.info("MQTT subscriber started")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT subscriber stopped")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            client.subscribe("pm25/sensor/#", qos=1)
            logger.info("Subscribed to pm25/sensor/#")
        else:
            logger.error(f"MQTT connect failed rc={reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code=None, properties=None):
        logger.warning(f"MQTT disconnected rc={reason_code}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            device_id = payload.get("device_id", "unknown")

            # 1. บันทึกลง InfluxDB
            write_sensor_reading(payload)

            # 2. Broadcast WebSocket
            if _loop and _loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast(device_id, payload), _loop
                )

            # 3. ตรวจ alert rules (async)
            if _loop and _loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._check_alerts(device_id, payload), _loop
                )

            logger.debug(f"Processed sensor data: device={device_id} pm2_5={payload.get('pm2_5')}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {msg.topic}")
        except Exception as e:
            logger.error(f"MQTT message error: {e}")

    async def _check_alerts(self, device_id: str, payload: dict):
        """ตรวจสอบ AlertRule และส่ง notification"""
        from app.database import SessionLocal
        from app.models.alert_rule import AlertRule
        from app.models.alert_log  import AlertLog
        from sqlalchemy import and_

        pm25 = float(payload.get("pm2_5", 0))
        aqi  = float(payload.get("aqi", 0))
        temp = float(payload.get("temperature", 0))

        metric_values = {"pm2_5": pm25, "aqi": aqi, "temperature": temp}

        db = SessionLocal()
        try:
            rules = db.query(AlertRule).filter(
                and_(AlertRule.device_id == device_id, AlertRule.is_active == True)
            ).all()

            for rule in rules:
                value = metric_values.get(rule.metric, 0)
                triggered = (
                    (rule.operator == ">"  and value >  rule.threshold) or
                    (rule.operator == ">=" and value >= rule.threshold) or
                    (rule.operator == "<"  and value <  rule.threshold) or
                    (rule.operator == "<=" and value <= rule.threshold)
                )
                if not triggered:
                    continue

                # ตรวจ cooldown — ดูการแจ้งเตือนล่าสุด
                last_log = (
                    db.query(AlertLog)
                    .filter_by(rule_id=rule.id)
                    .order_by(AlertLog.triggered_at.desc())
                    .first()
                )
                if last_log:
                    minutes_since = (
                        datetime.now(timezone.utc) - last_log.triggered_at.replace(tzinfo=timezone.utc)
                    ).total_seconds() / 60
                    if minutes_since < rule.cooldown_min:
                        continue  # ยังอยู่ใน cooldown

                # สร้างข้อความแจ้งเตือน
                message = (
                    f"⚠️ AirGuard Pi แจ้งเตือน\n"
                    f"Device: {device_id}\n"
                    f"{rule.metric.upper()} = {value:.1f} {rule.operator} {rule.threshold}\n"
                    f"PM2.5: {pm25:.1f} µg/m³ | AQI: {int(aqi)}\n"
                    f"มาตรฐาน PCD 2566: PM2.5 ≤ 37.5 µg/m³"
                )

                sent = await notify(rule.channel, message)

                # บันทึก log
                log = AlertLog(
                    rule_id=rule.id,
                    device_id=device_id,
                    metric=rule.metric,
                    value=value,
                    message=message,
                    channel=rule.channel,
                    sent_ok=sent,
                )
                db.add(log)
                db.commit()
                logger.info(f"Alert sent: {rule.channel} pm2_5={pm25:.1f}")

        finally:
            db.close()


# Singleton
mqtt_subscriber = MQTTSubscriber()
