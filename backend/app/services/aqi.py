"""
Thai AQI Calculator
อ้างอิง: กรมควบคุมมลพิษ (PCD) ประกาศ พ.ศ. 2566
URL: https://air4thai.pcd.go.th
"""

from dataclasses import dataclass


@dataclass
class AQIResult:
    aqi: int
    level: str
    level_en: str
    color: str
    description: str
    health_advice: str
    exceeds_standard: bool  # เกินมาตรฐาน 24-hr ไทย (37.5 µg/m³) หรือไม่


# Thai AQI Breakpoints (PM2.5, 24-hr average)
# อ้างอิง: กรมควบคุมมลพิษ พ.ศ. 2566
THAI_AQI_BREAKPOINTS = [
    #  pm_lo   pm_hi  aqi_lo  aqi_hi  level           level_en                color      description                          health_advice
    (  0.0,   15.0,    0,     25,  "ดีมาก",        "Very Good",       "#0EA5E9",  "คุณภาพอากาศดีมาก",          "สามารถทำกิจกรรมกลางแจ้งได้ตามปกติ"),
    ( 15.1,   25.0,   26,     50,  "ดี",           "Good",            "#22C55E",  "คุณภาพอากาศดี",             "สามารถทำกิจกรรมกลางแจ้งได้ตามปกติ"),
    ( 25.1,   37.5,   51,    100,  "ปานกลาง",      "Moderate",        "#EAB308",  "คุณภาพอากาศปานกลาง",        "กลุ่มเสี่ยงควรลดกิจกรรมกลางแจ้ง"),
    ( 37.6,   75.0,  101,    200,  "เริ่มมีผลต่อสุขภาพ", "Unhealthy (Sensitive)", "#F97316", "เริ่มมีผลกระทบต่อสุขภาพ", "ทุกคนควรลดกิจกรรมกลางแจ้ง สวม N95"),
    ( 75.1,  999.9,  201,    500,  "มีผลต่อสุขภาพ", "Unhealthy",      "#EF4444",  "มีผลกระทบต่อสุขภาพ",        "หลีกเลี่ยงกิจกรรมกลางแจ้งทุกชนิด"),
]

THAI_STANDARD_24H = 37.5  # µg/m³ (มาตรฐานไทย 2566)


def calculate_thai_aqi(pm25: float) -> AQIResult:
    """
    คำนวณ Thai AQI จากค่า PM2.5 (24-hr average)
    สูตร: AQI = ((IHi - ILo) / (CHi - CLo)) * (Cp - CLo) + ILo
    """
    pm25 = max(0.0, round(pm25, 1))

    for pm_lo, pm_hi, aqi_lo, aqi_hi, level, level_en, color, desc, advice in THAI_AQI_BREAKPOINTS:
        if pm_lo <= pm25 <= pm_hi:
            aqi = ((aqi_hi - aqi_lo) / (pm_hi - pm_lo)) * (pm25 - pm_lo) + aqi_lo
            return AQIResult(
                aqi=round(aqi),
                level=level,
                level_en=level_en,
                color=color,
                description=desc,
                health_advice=advice,
                exceeds_standard=(pm25 > THAI_STANDARD_24H),
            )

    # กรณีเกิน 999.9
    return AQIResult(
        aqi=500,
        level="มีผลต่อสุขภาพ",
        level_en="Hazardous",
        color="#7E0023",
        description="อันตรายมาก",
        health_advice="ห้ามออกนอกอาคารโดยเด็ดขาด",
        exceeds_standard=True,
    )


def get_fan_speed_recommendation(pm25: float) -> int:
    """
    Rule-based fan speed recommendation จาก PM2.5
    ใช้เป็น fallback เมื่อ AI model ไม่พร้อม
    Returns: fan speed percentage (0-100)
    """
    if pm25 <= 15.0:
        return 0    # ดีมาก: ปิดพัดลม
    elif pm25 <= 25.0:
        return 25   # ดี: ความเร็วต่ำ
    elif pm25 <= 37.5:
        return 50   # ปานกลาง: ความเร็วกลาง
    elif pm25 <= 75.0:
        return 75   # เริ่มมีผล: ความเร็วสูง
    else:
        return 100  # อันตราย: เต็มกำลัง
