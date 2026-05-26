"""
Sensor Router — ประวัติข้อมูล sensor + real-time (WebSocket)
"""

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.influx import query_history, query_latest, query_daily_avg
from app.ws.manager import ws_manager

router = APIRouter(tags=["sensor"])


@router.get("/latest/{device_id}")
async def get_latest(device_id: str):
    """ค่าล่าสุดของ device"""
    data = query_latest(device_id)
    if data is None:
        return {"error": "ไม่พบข้อมูล — device อาจออฟไลน์อยู่"}
    return data


@router.get("/history/{device_id}")
async def get_history(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),   # 1 ชม. – 7 วัน
):
    """ประวัติข้อมูล sensor (default 24 ชั่วโมง)"""
    data = query_history(device_id, hours=hours)
    return {"device_id": device_id, "hours": hours, "count": len(data), "data": data}


@router.get("/daily-avg/{device_id}")
async def get_daily_avg(
    device_id: str,
    days: int = Query(7, ge=1, le=30),
):
    """ค่าเฉลี่ย PM2.5 รายวัน"""
    data = query_daily_avg(device_id, days=days)
    return {"device_id": device_id, "days": days, "data": data}


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket — push ข้อมูล real-time ไปยัง client"""
    await ws_manager.connect(websocket, device_id)
    try:
        while True:
            await websocket.receive_text()   # keep-alive ping
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, device_id)
