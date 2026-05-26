"""
Database connections — InfluxDB 2.x (time-series) + SQLite (relational)
"""

import logging
from contextlib import asynccontextmanager

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# ── SQLite (users, devices, alert rules) ─────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """สร้างตาราง SQLite ทั้งหมดถ้ายังไม่มี"""
    from app.models import user, device, alert_rule, alert_log  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite tables ready")


def get_db():
    """FastAPI dependency — SQLite session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── InfluxDB 2.x (sensor time-series) ────────────────────────────────────────

_influx_client: InfluxDBClient | None = None


def get_influx_client() -> InfluxDBClient:
    global _influx_client
    if _influx_client is None:
        _influx_client = InfluxDBClient(
            url=settings.INFLUX_URL,
            token=settings.INFLUX_TOKEN,
            org=settings.INFLUX_ORG,
            timeout=10_000,
        )
        logger.info(f"InfluxDB connected → {settings.INFLUX_URL}")
    return _influx_client


def get_write_api():
    """Synchronous write API (ใช้ใน MQTT subscriber)"""
    return get_influx_client().write_api(write_options=SYNCHRONOUS)


def get_query_api():
    """Query API (ใช้ใน sensor router)"""
    return get_influx_client().query_api()


def close_influx():
    global _influx_client
    if _influx_client:
        _influx_client.close()
        _influx_client = None
        logger.info("InfluxDB connection closed")


# ── Lifespan helpers ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan_db(_):
    """ใช้ใน FastAPI lifespan — init ตอนเริ่ม, cleanup ตอนปิด"""
    init_db()
    get_influx_client()          # warm up connection
    yield
    close_influx()
