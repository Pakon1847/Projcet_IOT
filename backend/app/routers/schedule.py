"""
Schedule Router — CRUD สำหรับ FanSchedule
POST   /api/schedule/        สร้าง schedule ใหม่
GET    /api/schedule/        ดึง schedule ทั้งหมด
GET    /api/schedule/{id}    ดึง schedule เดียว
PUT    /api/schedule/{id}    อัพเดต schedule
DELETE /api/schedule/{id}    ลบ schedule
PATCH  /api/schedule/{id}/toggle  เปิด/ปิด is_active
GET    /api/schedule/active  ดึงเฉพาะที่ active
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.models.schedule import FanSchedule

router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    name:       str         = Field(..., min_length=1, max_length=100, example="กลางคืน")
    days:       str         = Field("1111111", pattern=r"^[01]{7}$", example="1111111")
    start_time: str         = Field(..., pattern=r"^\d{2}:\d{2}$", example="22:00")
    end_time:   str         = Field(..., pattern=r"^\d{2}:\d{2}$", example="06:00")
    fan_speed:  int         = Field(60, ge=0, le=100)
    is_active:  bool        = True


class ScheduleUpdate(BaseModel):
    name:       Optional[str] = Field(None, min_length=1, max_length=100)
    days:       Optional[str] = Field(None, pattern=r"^[01]{7}$")
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time:   Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    fan_speed:  Optional[int] = Field(None, ge=0, le=100)
    is_active:  Optional[bool] = None


class ScheduleOut(BaseModel):
    id:         int
    name:       str
    days:       str
    start_time: str
    end_time:   str
    fan_speed:  int
    is_active:  bool

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ScheduleOut, status_code=201)
def create_schedule(body: ScheduleCreate, db: Session = Depends(get_db)):
    """สร้าง schedule ใหม่"""
    sched = FanSchedule(**body.model_dump())
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


@router.get("/", response_model=list[ScheduleOut])
def list_schedules(db: Session = Depends(get_db)):
    """ดึง schedule ทั้งหมด"""
    return db.query(FanSchedule).order_by(FanSchedule.id).all()


@router.get("/active", response_model=list[ScheduleOut])
def list_active_schedules(db: Session = Depends(get_db)):
    """ดึงเฉพาะ schedule ที่ active"""
    return db.query(FanSchedule).filter(FanSchedule.is_active == True).all()


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = db.get(FanSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return sched


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, body: ScheduleUpdate, db: Session = Depends(get_db)):
    sched = db.get(FanSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(sched, field, value)
    db.commit()
    db.refresh(sched)
    return sched


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = db.get(FanSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(sched)
    db.commit()


@router.patch("/{schedule_id}/toggle", response_model=ScheduleOut)
def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """สลับ is_active เปิด/ปิด"""
    sched = db.get(FanSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    sched.is_active = not sched.is_active
    db.commit()
    db.refresh(sched)
    return sched
