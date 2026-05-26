"""
AI Router — PM2.5 Prediction + AI Chat (Ollama Phi-3 Mini)
"""

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.services.influx import query_history

router = APIRouter(tags=["ai"])


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    device_id: str
    message:   str


@router.post("/chat")
async def ai_chat(req: ChatRequest):
    """
    AI Chat ผ่าน Ollama (Phi-3 Mini local)
    ดึงข้อมูล sensor ล่าสุดเป็น context ก่อนถาม
    """
    # ดึงข้อมูลล่าสุด 1 ชั่วโมง เป็น context
    history = query_history(req.device_id, hours=1)
    if history:
        last = history[-1]
        context = (
            f"ข้อมูลล่าสุด: PM2.5={last.get('pm2_5')} µg/m³, "
            f"AQI={last.get('aqi')}, "
            f"อุณหภูมิ={last.get('temperature')}°C, "
            f"ความชื้น={last.get('humidity')}% "
            f"(มาตรฐาน PCD 2566: PM2.5 ≤ 37.5 µg/m³)"
        )
    else:
        context = "ยังไม่มีข้อมูล sensor"

    system_prompt = (
        "คุณคือผู้ช่วย AI สำหรับระบบฟอกอากาศ PM2.5 "
        "ตอบเป็นภาษาไทย กระชับ ชัดเจน อ้างอิงมาตรฐานกรมควบคุมมลพิษ พ.ศ. 2566 "
        f"ข้อมูล sensor ปัจจุบัน: {context}"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json={
                    "model":  settings.OLLAMA_MODEL,
                    "prompt": req.message,
                    "system": system_prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {"response": data.get("response", ""), "context_used": context}

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Ollama ไม่พร้อมใช้งาน — ตรวจสอบว่า ollama serve กำลังทำงานอยู่",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Prediction (placeholder — จะเชื่อม LSTM TFLite ในภายหลัง) ───────────────

@router.get("/predict/{device_id}")
async def predict_pm25(device_id: str, hours_ahead: int = 1):
    """
    ทำนาย PM2.5 ล่วงหน้า (ใช้ LSTM TFLite)
    Phase 1: rule-based placeholder
    Phase 2: เชื่อม ml/models/pm25_lstm.tflite
    """
    history = query_history(device_id, hours=6)
    if len(history) < 3:
        raise HTTPException(status_code=422, detail="ข้อมูลไม่เพียงพอสำหรับการทำนาย")

    # Placeholder: moving average ของ 3 ค่าล่าสุด
    recent = [r["pm2_5"] for r in history[-3:] if r.get("pm2_5")]
    predicted = round(sum(recent) / len(recent), 1) if recent else None

    return {
        "device_id":    device_id,
        "hours_ahead":  hours_ahead,
        "predicted_pm25": predicted,
        "note": "Phase 1: moving average — LSTM TFLite จะถูกใช้เมื่อ model training เสร็จ",
    }
