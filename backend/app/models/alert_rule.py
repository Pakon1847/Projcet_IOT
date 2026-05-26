from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Float, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AlertRule(Base):
    """กฎการแจ้งเตือน — เช่น PM2.5 > 37.5 → ส่ง LINE"""
    __tablename__ = "alert_rules"

    id:          Mapped[int]   = mapped_column(primary_key=True)
    device_id:   Mapped[str]   = mapped_column(String(50), index=True)
    metric:      Mapped[str]   = mapped_column(String(20))   # "pm2_5" | "aqi" | "temperature"
    operator:    Mapped[str]   = mapped_column(String(5))    # ">" | "<" | ">=" | "<="
    threshold:   Mapped[float] = mapped_column(Float)
    channel:     Mapped[str]   = mapped_column(String(20))   # "line" | "telegram"
    is_active:   Mapped[bool]  = mapped_column(Boolean, default=True)
    cooldown_min: Mapped[int]  = mapped_column(Integer, default=30)  # นาที ก่อนแจ้งซ้ำ
    owner_id:    Mapped[int]   = mapped_column(ForeignKey("users.id"))
    created_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner = relationship("User", backref="alert_rules")
