from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AlertLog(Base):
    """ประวัติการแจ้งเตือนที่ส่งออกไปแล้ว"""
    __tablename__ = "alert_logs"

    id:          Mapped[int]   = mapped_column(primary_key=True)
    rule_id:     Mapped[int]   = mapped_column(ForeignKey("alert_rules.id"))
    device_id:   Mapped[str]   = mapped_column(String(50))
    metric:      Mapped[str]   = mapped_column(String(20))
    value:       Mapped[float] = mapped_column(Float)
    message:     Mapped[str]   = mapped_column(Text, default="")
    channel:     Mapped[str]   = mapped_column(String(20))
    sent_ok:     Mapped[bool]  = mapped_column(default=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rule = relationship("AlertRule", backref="logs")
