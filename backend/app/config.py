from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME:    str  = "PM2.5 Smart Air Purifier API"
    APP_VERSION: str  = "1.0.0"
    DEBUG:       bool = False

    # JWT
    SECRET_KEY:         str = "change-this-in-production"
    JWT_ALGORITHM:      str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440   # 24 ชั่วโมง

    # InfluxDB
    INFLUX_URL:    str = "http://localhost:8086"
    INFLUX_TOKEN:  str = ""
    INFLUX_ORG:    str = "airguard"
    INFLUX_BUCKET: str = "pm25_data"

    # SQLite
    DATABASE_URL: str = "sqlite:////data/pm25.db"

    # MQTT
    MQTT_BROKER: str = "localhost"
    MQTT_PORT:   int = 1883

    # Notifications
    LINE_NOTIFY_TOKEN:  str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID:   str = ""

    # Ollama (AI Chat — local LLM)
    OLLAMA_HOST:  str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"

    # Thai AQI Standard (กรมควบคุมมลพิษ พ.ศ. 2566)
    PM25_STANDARD_24H:  float = 37.5
    PM25_STANDARD_YEAR: float = 15.0

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# singleton ใช้ทั่ว app
settings = get_settings()
