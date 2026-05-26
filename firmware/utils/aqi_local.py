"""
Thai AQI Calculator (สำหรับ Firmware บน Pi 4)
มาตรฐาน: กรมควบคุมมลพิษ (PCD) พ.ศ. 2566
- PM2.5 24-hr: 37.5 µg/m³
- 5 ระดับ AQI: ดีมาก / ดี / ปานกลาง / เริ่มมีผลต่อสุขภาพ / มีผลต่อสุขภาพ
"""

from dataclasses import dataclass

# (C_low, C_high, AQI_low, AQI_high, level_th, level_en)
THAI_AQI_BREAKPOINTS = [
    (0.0,  15.0,   0,  25, "ดีมาก",              "Very Good"),
    (15.1, 25.0,  26,  50, "ดี",                 "Good"),
    (25.1, 37.5,  51, 100, "ปานกลาง",            "Moderate"),
    (37.6, 75.0, 101, 200, "เริ่มมีผลต่อสุขภาพ", "Unhealthy for Sensitive"),
    (75.1, 999.9,201, 500, "มีผลต่อสุขภาพ",      "Unhealthy"),
]

PM25_STANDARD_24H = 37.5  # µg/m³  (PCD 2566)


@dataclass
class AQIResult:
    aqi:              int
    level:            str   # ภาษาไทย
    level_en:         str
    exceeds_standard: bool
    fan_speed_pct:    int   # 0-100 — rule-based recommendation


def calculate_thai_aqi(pm25: float) -> AQIResult:
    """
    คำนวณ Thai AQI จากค่า PM2.5 (µg/m³)
    คืนค่า AQIResult พร้อม level และ fan speed แนะนำ
    """
    pm25 = max(0.0, float(pm25))

    for c_lo, c_hi, aqi_lo, aqi_hi, level, level_en in THAI_AQI_BREAKPOINTS:
        if pm25 <= c_hi:
            # Linear interpolation
            aqi = aqi_lo + (pm25 - c_lo) / (c_hi - c_lo) * (aqi_hi - aqi_lo)
            aqi = int(round(aqi))
            return AQIResult(
                aqi=aqi,
                level=level,
                level_en=level_en,
                exceeds_standard=(pm25 > PM25_STANDARD_24H),
                fan_speed_pct=_recommend_fan_speed(aqi),
            )

    # เกิน 75 µg/m³ — ระดับ 5
    return AQIResult(
        aqi=500,
        level="มีผลต่อสุขภาพ",
        level_en="Unhealthy",
        exceeds_standard=True,
        fan_speed_pct=100,
    )


def _recommend_fan_speed(aqi: int) -> int:
    """Rule-based fan speed จาก AQI (fallback เมื่อ AI ไม่พร้อม)"""
    if aqi <= 25:   return 20   # ดีมาก  — หมุนเบา
    if aqi <= 50:   return 40   # ดี
    if aqi <= 100:  return 60   # ปานกลาง
    if aqi <= 200:  return 80   # เริ่มมีผล
    return 100                  # มีผลต่อสุขภาพ — เต็มสปีด


# ── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_values = [5, 15, 25, 37.5, 50, 75, 100]
    print(f"{'PM2.5':>8}  {'AQI':>5}  {'Level':<28}  {'Fan%':>5}  Exceed?")
    print("-" * 65)
    for v in test_values:
        r = calculate_thai_aqi(v)
        print(f"{v:>8.1f}  {r.aqi:>5}  {r.level:<28}  {r.fan_speed_pct:>5}%  {'⚠️' if r.exceeds_standard else '✓'}")
