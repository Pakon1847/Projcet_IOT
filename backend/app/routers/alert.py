"""
Alert Router — จัดการกฎการแจ้งเตือนและประวัติ
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert_rule import AlertRule
from app.models.alert_log  import AlertLog

router = APIRouter(tags=["alert"])


class AlertRuleIn(BaseModel):
    device_id:    str
    metric:       str   = "pm2_5"         # pm2_5 | aqi | temperature
    operator:     str   = ">"
    threshold:    float = 37.5
    channel:      str   = "line"          # line | telegram
    cooldown_min: int   = 30
    owner_id:     int   = 1


@router.get("/rules/{device_id}")
def list_rules(device_id: str, db: Session = Depends(get_db)):
    """ดูกฎทั้งหมดของ device"""
    rules = db.query(AlertRule).filter_by(device_id=device_id).all()
    return rules


@router.post("/rules")
def create_rule(rule_in: AlertRuleIn, db: Session = Depends(get_db)):
    """สร้างกฎใหม่"""
    rule = AlertRule(**rule_in.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """ลบกฎ"""
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="ไม่พบกฎ")
    db.delete(rule)
    db.commit()
    return {"ok": True}


@router.get("/logs/{device_id}")
def alert_logs(device_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """ประวัติการแจ้งเตือน"""
    logs = (
        db.query(AlertLog)
        .filter_by(device_id=device_id)
        .order_by(AlertLog.triggered_at.desc())
        .limit(limit)
        .all()
    )
    return logs
