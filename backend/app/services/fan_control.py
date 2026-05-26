"""
Fan control service — ส่งคำสั่งไปยัง firmware ผ่าน MQTT
"""

import json
import logging

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from app.config import settings

logger = logging.getLogger(__name__)

_mqtt_client: mqtt.Client | None = None


def get_mqtt_client() -> mqtt.Client:
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id="backend_api",
        )
        _mqtt_client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
        _mqtt_client.loop_start()
        logger.info("Backend MQTT client connected")
    return _mqtt_client


def set_fan_speed(device_id: str, speed: int, mode: str = "manual") -> bool:
    """ส่งคำสั่งตั้งความเร็วพัดลมผ่าน MQTT"""
    speed = max(0, min(100, int(speed)))
    payload = {"speed": speed, "mode": mode}
    topic   = f"pm25/fan/{device_id}/set"
    try:
        client = get_mqtt_client()
        result = client.publish(topic, json.dumps(payload), qos=1)
        return result.rc == mqtt.MQTT_ERR_SUCCESS
    except Exception as e:
        logger.error(f"Fan control MQTT error: {e}")
        return False


def disconnect_mqtt():
    global _mqtt_client
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        _mqtt_client = None
