"""
Outdoor Air Service — Air4Thai API (กรมควบคุมมลพิษ)
ดึงข้อมูล PM2.5 นอกบ้านจาก API จริงของ PCD
cache ไว้ 30 นาทีเพื่อไม่ให้ยิง API บ่อยเกินไป
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Air4Thai API endpoint (ไม่ต้อง API key)
AIR4THAI_URL = "http://air4thai.pcd.go.th/services/getNewAQI_JSON.php"

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache: dict = {}
_cache_time: Optional[datetime] = None
_CACHE_TTL = timedelta(minutes=30)


def _is_cache_valid() -> bool:
    if _cache_time is None:
        return False
    return datetime.now(timezone.utc) - _cache_time < _CACHE_TTL


async def _fetch_air4thai() -> list[dict]:
    """ดึงข้อมูลสถานีทั้งหมดจาก Air4Thai API"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(AIR4THAI_URL)
            resp.raise_for_status()
            data = resp.json()
            return data.get("CONTENT", [])
    except Exception as e:
        logger.error(f"Air4Thai fetch error: {e}")
        return []


def _parse_station(station: dict) -> Optional[dict]:
    """แปลง raw station data เป็น dict ที่ใช้งานง่าย"""
    try:
        pm25_raw = station.get("PM25", {})
        pm25_val = pm25_raw.get("value", "-")
        aqi_val  = pm25_raw.get("aqi",   "-")

        return {
            "station_id":   station.get("stationID", ""),
            "name_th":      station.get("nameTH", ""),
            "name_en":      station.get("nameEN", ""),
            "area_th":      station.get("areaTH", ""),
            "lat":          float(station.get("lat", 0)),
            "lon":          float(station.get("long", 0)),
            "pm25":         float(pm25_val) if pm25_val not in ("-", "", None) else None,
            "aqi":          int(aqi_val)    if aqi_val  not in ("-", "", None) else None,
            "color":        pm25_raw.get("color", "#808080"),
            "updated_at":   station.get("date", "") + " " + station.get("time", ""),
        }
    except Exception:
        return None


async def get_all_stations(force_refresh: bool = False) -> list[dict]:
    """ดึงข้อมูลทุกสถานี (cached 30 นาที)"""
    global _cache, _cache_time

    if not force_refresh and _is_cache_valid() and _cache:
        return list(_cache.values())

    stations_raw = await _fetch_air4thai()
    result = {}
    for s in stations_raw:
        parsed = _parse_station(s)
        if parsed and parsed["pm25"] is not None:
            result[parsed["station_id"]] = parsed

    if result:
        _cache = result
        _cache_time = datetime.now(timezone.utc)
        logger.info(f"Air4Thai: updated {len(result)} stations")

    return list(result.values())


async def get_station(station_id: str) -> Optional[dict]:
    """ดึงข้อมูลสถานีเดียว"""
    stations = await get_all_stations()
    return next((s for s in stations if s["station_id"] == station_id), None)


async def get_nearest_station(lat: float, lon: float) -> Optional[dict]:
    """หาสถานีที่ใกล้ที่สุด (ใช้ Euclidean distance อย่างง่าย)"""
    stations = await get_all_stations()
    if not stations:
        return None

    def dist(s: dict) -> float:
        return (s["lat"] - lat) ** 2 + (s["lon"] - lon) ** 2

    return min(stations, key=dist)


# ── Smart Ventilation Logic ───────────────────────────────────────────────────

def ventilation_advice(indoor_pm25: float, outdoor_pm25: Optional[float]) -> dict:
    """
    ตัดสินใจว่าควรเปิดหน้าต่าง/พัดลมระบายอากาศหรือไม่

    Logic:
      - ถ้า outdoor_pm25 is None → ไม่มีข้อมูล
      - ถ้า outdoor < indoor - 10 AND outdoor < 37.5 → เปิดหน้าต่างได้ (อากาศนอกดีกว่า)
      - ถ้า outdoor < 37.5 → อากาศนอกอยู่ในเกณฑ์ แต่ indoor ก็ดีอยู่แล้ว
      - ถ้า outdoor >= 37.5 → อากาศนอกแย่ ปิดหน้าต่างไว้
    """
    GOOD_THRESHOLD = 37.5   # มาตรฐาน PCD 2566

    if outdoor_pm25 is None:
        return {
            "action": "unknown",
            "icon":   "❓",
            "title":  "ไม่มีข้อมูลอากาศนอก",
            "detail": "ไม่สามารถดึงข้อมูลสถานีตรวจวัดได้",
            "color":  "slate",
        }

    if outdoor_pm25 < GOOD_THRESHOLD and outdoor_pm25 < indoor_pm25 - 10:
        return {
            "action": "open",
            "icon":   "🪟",
            "title":  "เปิดหน้าต่างได้",
            "detail": f"PM2.5 นอกบ้าน ({outdoor_pm25:.1f}) ต่ำกว่าในบ้าน ({indoor_pm25:.1f}) — อากาศนอกดีกว่า",
            "color":  "emerald",
        }
    elif outdoor_pm25 < GOOD_THRESHOLD:
        return {
            "action": "optional",
            "icon":   "🌿",
            "title":  "อากาศนอกอยู่ในเกณฑ์ดี",
            "detail": f"PM2.5 นอกบ้าน {outdoor_pm25:.1f} µg/m³ — เปิดหน้าต่างได้ถ้าต้องการอากาศบริสุทธิ์",
            "color":  "sky",
        }
    else:
        return {
            "action": "close",
            "icon":   "🚪",
            "title":  "ปิดหน้าต่างไว้",
            "detail": f"PM2.5 นอกบ้าน {outdoor_pm25:.1f} µg/m³ เกินมาตรฐาน — ใช้เครื่องฟอกอากาศต่อไป",
            "color":  "red",
        }
