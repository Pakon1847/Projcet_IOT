"""
Schedule Model — ตั้งเวลาพัดลมอัตโนมัติ
เก็บใน SQLite ผ่าน SQLAlchemy
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from app.database import Base


class FanSchedule(Base):
    __tablename__ = "fan_schedules"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)          # ชื่อ schedule เช่น "กลางคืน"

    # วัน: "1111111" = ทุกวัน, "1000001" = จันทร์+อาทิตย์
    # ตำแหน่ง 0=จันทร์ ... 6=อาทิตย์
    days        = Column(String(7), default="1111111")

    start_time  = Column(String(5), nullable=False)            # "HH:MM" เช่น "22:00"
    end_time    = Column(String(5), nullable=False)            # "HH:MM" เช่น "06:00"
    fan_speed   = Column(Integer, nullable=False, default=60)  # 0–100 %
    is_active   = Column(Boolean, default=True)

    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime,
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<FanSchedule {self.name} {self.start_time}-{self.end_time} {self.fan_speed}%>"
