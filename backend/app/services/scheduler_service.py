"""
Scheduler Service — รัน FanSchedule อัตโนมัติด้วย APScheduler
ทุกๆ 1 นาที จะตรวจว่าตอนนี้ควรเปิดหรือปิดพัดลมหรือไม่

Logic:
  1. โหลด schedule ที่ is_active=True ทั้งหมดจาก DB
  2. ตรวจวันและเวลาปัจจุบัน (TZ: Asia/Bangkok)
  3. ถ้าตรงกับ schedule → publish MQTT command ไปยัง firmware
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import SessionLocal
from app.models.schedule import FanSchedule

logger = logging.getLogger(__name__)

TZ_BANGKOK = ZoneInfo("Asia/Bangkok")

# ── APScheduler instance ──────────────────────────────────────────────────────
_scheduler = AsyncIOScheduler(timezone="Asia/Bangkok")


# ── MQTT helper ───────────────────────────────────────────────────────────────

def _publish_fan_command(speed: int):
    """Publish fan speed command ผ่าน MQTT (fire-and-forget)"""
    try:
        client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id="scheduler_pub",
        )
        client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=10)
        payload = json.dumps({"speed": speed, "source": "schedule"})
        client.publish("pm25/fan/set", payload, qos=1)
        client.disconnect()
        logger.info(f"Schedule: published fan speed={speed}%")
    except Exception as e:
        logger.error(f"Schedule MQTT publish failed: {e}")


# ── Main job ──────────────────────────────────────────────────────────────────

async def _check_schedules():
    """
    ตรวจ schedule ทุก 1 นาที
    - เปรียบเทียบเวลาปัจจุบัน (Bangkok) กับ start_time / end_time
    - ถ้าอยู่ใน window → set fan_speed
    - ถ้าไม่มี schedule ที่ match → ไม่ทำอะไร (ให้ manual override ทำงาน)
    """
    now_bkk = datetime.now(TZ_BANGKOK)
    day_idx  = now_bkk.weekday()          # 0=จันทร์ ... 6=อาทิตย์
    now_str  = now_bkk.strftime("%H:%M")  # "HH:MM"

    db = SessionLocal()
    try:
        schedules = db.query(FanSchedule).filter(FanSchedule.is_active == True).all()

        for sched in schedules:
            # ตรวจวัน
            if len(sched.days) != 7 or sched.days[day_idx] != "1":
                continue

            # ตรวจเวลา — รองรับ overnight (เช่น 22:00-06:00)
            if _in_time_window(now_str, sched.start_time, sched.end_time):
                logger.info(
                    f"Schedule '{sched.name}' active → fan {sched.fan_speed}%"
                )
                _publish_fan_command(sched.fan_speed)
                return   # ใช้ schedule แรกที่ตรงเท่านั้น

    finally:
        db.close()


def _in_time_window(current: str, start: str, end: str) -> bool:
    """
    ตรวจว่า current อยู่ใน [start, end) หรือไม่
    รองรับ overnight: start="22:00" end="06:00"
    """
    if start <= end:
        return start <= current < end
    else:
        # overnight: current >= start OR current < end
        return current >= start or current < end


# ── Public API ────────────────────────────────────────────────────────────────

def start_scheduler():
    """เรียกตอน FastAPI startup"""
    _scheduler.add_job(
        _check_schedules,
        trigger="cron",
        minute="*",     # ทุกนาที
        id="fan_schedule_checker",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Fan scheduler started (checks every minute)")


def stop_scheduler():
    """เรียกตอน FastAPI shutdown"""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Fan scheduler stopped")
