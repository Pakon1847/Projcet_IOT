"""
Fan Router — ควบคุมพัดลมผ่าน API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.fan_control import set_fan_speed

router = APIRouter(tags=["fan"])


class FanCommand(BaseModel):
    speed: int  = Field(..., ge=0, le=100, description="ความเร็วพัดลม 0-100%")
    mode:  str  = Field("manual", pattern="^(manual|auto)$")


@router.post("/set/{device_id}")
async def control_fan(device_id: str, cmd: FanCommand):
    """ตั้งความเร็วพัดลมผ่าน MQTT"""
    ok = set_fan_speed(device_id, cmd.speed, cmd.mode)
    if not ok:
        raise HTTPException(status_code=503, detail="ไม่สามารถส่งคำสั่งไปยัง device ได้")
    return {"device_id": device_id, "speed": cmd.speed, "mode": cmd.mode, "ok": True}


@router.post("/auto/{device_id}")
async def set_auto_mode(device_id: str):
    """สลับพัดลมเป็น Auto mode"""
    ok = set_fan_speed(device_id, speed=0, mode="auto")
    if not ok:
        raise HTTPException(status_code=503, detail="ไม่สามารถส่งคำสั่งได้")
    return {"device_id": device_id, "mode": "auto"}


@router.post("/off/{device_id}")
async def turn_off_fan(device_id: str):
    """ปิดพัดลม"""
    ok = set_fan_speed(device_id, speed=0, mode="manual")
    if not ok:
        raise HTTPException(status_code=503, detail="ไม่สามารถส่งคำสั่งได้")
    return {"device_id": device_id, "speed": 0, "mode": "manual"}
