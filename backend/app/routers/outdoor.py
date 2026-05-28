"""
Outdoor Air Router — ข้อมูล PM2.5 นอกบ้านจาก Air4Thai API
"""

from fastapi import APIRouter, Query
from app.services import outdoor_air

router = APIRouter()


@router.get("/stations")
async def list_stations(force_refresh: bool = False):
    """ดึงข้อมูลสถานีตรวจวัดทั้งหมดในประเทศไทย"""
    stations = await outdoor_air.get_all_stations(force_refresh=force_refresh)
    return {"count": len(stations), "stations": stations}


@router.get("/nearest")
async def nearest_station(
    lat: float = Query(..., description="Latitude of indoor device"),
    lon: float = Query(..., description="Longitude of indoor device"),
):
    """หาสถานีที่ใกล้ที่สุดและคำแนะนำการระบายอากาศ"""
    station = await outdoor_air.get_nearest_station(lat, lon)
    return {"station": station}


@router.get("/advice")
async def ventilation_advice(
    indoor_pm25: float = Query(..., description="Current indoor PM2.5"),
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    คำแนะนำว่าควรเปิดหน้าต่างหรือไม่
    เปรียบเทียบ indoor กับ outdoor ที่สถานีใกล้ที่สุด
    """
    station = await outdoor_air.get_nearest_station(lat, lon)
    outdoor_pm25 = station["pm25"] if station else None

    advice = outdoor_air.ventilation_advice(indoor_pm25, outdoor_pm25)

    return {
        "advice":   advice,
        "station":  station,
        "indoor_pm25": indoor_pm25,
    }


@router.get("/station/{station_id}")
async def get_station(station_id: str):
    """ดึงข้อมูลสถานีเฉพาะ"""
    station = await outdoor_air.get_station(station_id)
    if not station:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Station not found")
    return station
