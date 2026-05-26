from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id:          Mapped[int]      = mapped_column(primary_key=True)
    device_id:   Mapped[str]      = mapped_column(String(50), unique=True, index=True)
    name:        Mapped[str]      = mapped_column(String(100))
    location:    Mapped[str]      = mapped_column(String(200), default="")
    is_online:   Mapped[bool]     = mapped_column(Boolean, default=False)
    owner_id:    Mapped[int]      = mapped_column(ForeignKey("users.id"))
    fan_mode:    Mapped[str]      = mapped_column(String(10), default="auto")
    fan_speed:   Mapped[int]      = mapped_column(Integer, default=0)
    last_seen:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner = relationship("User", backref="devices")
