"""
Anomaly Detection Service — ตรวจจับ PM2.5 พุ่งสูงผิดปกติ
ใช้ Rolling Window + Rate of Change

ตัวอย่างกรณีที่ detect ได้:
  - จุดธูป → PM2.5 พุ่ง 30+ µg/m³ ใน 2 นาที
  - ทำอาหาร → PM2.5 พุ่งเร็วต่อเนื่อง
  - ไฟไหม้ข้างบ้าน → PM2.5 สูงผิดปกติมาก
"""

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
WINDOW_SIZE        = 12       # เก็บค่าย้อนหลัง 12 readings (~2 นาทีที่ interval 10s)
SPIKE_THRESHOLD    = 25.0     # µg/m³ — ถ้า PM2.5 เพิ่มเกินนี้ใน 1 นาที = spike
ABSOLUTE_THRESHOLD = 150.0    # µg/m³ — ถ้า PM2.5 เกินนี้ทันที = critical
COOLDOWN_SECONDS   = 600      # 10 นาที ไม่แจ้งซ้ำ

# ── State (per device) ────────────────────────────────────────────────────────
# device_id → deque of (timestamp, pm25)
_windows: dict[str, deque] = {}
# device_id → last anomaly time
_last_alert: dict[str, datetime] = {}


def _get_window(device_id: str) -> deque:
    if device_id not in _windows:
        _windows[device_id] = deque(maxlen=WINDOW_SIZE)
    return _windows[device_id]


def _in_cooldown(device_id: str) -> bool:
    last = _last_alert.get(device_id)
    if last is None:
        return False
    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    return elapsed < COOLDOWN_SECONDS


def check(device_id: str, pm25: float) -> Optional[dict]:
    """
    เพิ่มค่า PM2.5 เข้า window แล้วตรวจสอบ anomaly
    คืน dict ถ้าพบ anomaly, None ถ้าปกติ
    """
    now    = datetime.now(timezone.utc)
    window = _get_window(device_id)
    window.append((now, pm25))

    # ยังอยู่ใน cooldown
    if _in_cooldown(device_id):
        return None

    # ต้องมีข้อมูลอย่างน้อย 6 readings ก่อนตรวจ
    if len(window) < 6:
        return None

    # ── ตรวจ 1: Critical absolute value ──────────────────────────────────────
    if pm25 >= ABSOLUTE_THRESHOLD:
        _last_alert[device_id] = now
        return _build_alert(
            anomaly_type = "critical",
            device_id    = device_id,
            current_pm25 = pm25,
            message      = f"🚨 PM2.5 วิกฤต! {pm25:.1f} µg/m³ — อยู่ในพื้นที่ที่เป็นอันตราย กรุณาออกจากห้อง!",
        )

    # ── ตรวจ 2: Rate of change (spike) ───────────────────────────────────────
    # เปรียบเทียบ current กับค่าเฉลี่ย 6 readings แรกใน window
    baseline_readings = list(window)[: len(window) // 2]
    baseline_avg = sum(r[1] for r in baseline_readings) / len(baseline_readings)
    rate_of_change = pm25 - baseline_avg

    if rate_of_change >= SPIKE_THRESHOLD:
        _last_alert[device_id] = now
        return _build_alert(
            anomaly_type = "spike",
            device_id    = device_id,
            current_pm25 = pm25,
            message      = (
                f"⚠️ PM2.5 พุ่งสูงผิดปกติ! {pm25:.1f} µg/m³ "
                f"(เพิ่มขึ้น +{rate_of_change:.1f} µg/m³ ใน ~1 นาที)\n"
                f"อาจมีการจุดธูป, ทำอาหาร หรือมีควัน — เปิดเครื่องฟอกอากาศเต็มกำลัง"
            ),
        )

    return None


def _build_alert(
    anomaly_type: str,
    device_id: str,
    current_pm25: float,
    message: str,
) -> dict:
    logger.warning(f"Anomaly detected [{anomaly_type}] device={device_id} pm25={current_pm25:.1f}")
    return {
        "type":     anomaly_type,
        "device_id": device_id,
        "pm25":     current_pm25,
        "message":  message,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def get_window_stats(device_id: str) -> dict:
    """ดึงสถิติ window ปัจจุบัน (สำหรับ debug / display)"""
    window = _get_window(device_id)
    if not window:
        return {"count": 0, "min": None, "max": None, "avg": None}
    values = [r[1] for r in window]
    return {
        "count": len(values),
        "min":   round(min(values), 1),
        "max":   round(max(values), 1),
        "avg":   round(sum(values) / len(values), 1),
    }
