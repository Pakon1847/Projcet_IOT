import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Device
    DEVICE_ID: str     = os.getenv("DEVICE_ID", "pi4_home_001")
    DEVICE_NAME: str   = os.getenv("DEVICE_NAME", "เครื่องฟอกอากาศ")

    # MQTT
    MQTT_BROKER: str   = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int     = int(os.getenv("MQTT_PORT", "1883"))

    # Sensor
    PMS5003_PORT: str  = os.getenv("PMS5003_PORT", "/dev/ttyS0")
    FAN_GPIO_PIN: int  = int(os.getenv("FAN_GPIO_PIN", "18"))  # PWM pin

    # Collection interval
    SENSOR_INTERVAL: int = int(os.getenv("SENSOR_INTERVAL", "10"))  # วินาที
