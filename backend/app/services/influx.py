"""
InfluxDB query helpers — sensor history, aggregations
"""

from datetime import datetime, timezone
from typing import Any

from influxdb_client import Point

from app.config import settings
from app.database import get_write_api, get_query_api


MEASUREMENT = "pm25_sensor"


# ── Write ─────────────────────────────────────────────────────────────────────

def write_sensor_reading(payload: dict) -> None:
    """บันทึกค่า sensor ลง InfluxDB"""
    point = (
        Point(MEASUREMENT)
        .tag("device_id", payload["device_id"])
        .field("pm1_0",       float(payload.get("pm1_0", 0)))
        .field("pm2_5",       float(payload["pm2_5"]))
        .field("pm10",        float(payload.get("pm10", 0)))
        .field("temperature", float(payload.get("temperature", 0)))
        .field("humidity",    float(payload.get("humidity", 0)))
        .field("pressure",    float(payload.get("pressure", 0)))
        .field("aqi",         int(payload.get("aqi", 0)))
        .time(payload.get("timestamp", datetime.now(timezone.utc)))
    )
    write_api = get_write_api()
    write_api.write(
        bucket=settings.INFLUX_BUCKET,
        org=settings.INFLUX_ORG,
        record=point,
    )


# ── Query ─────────────────────────────────────────────────────────────────────

def query_history(device_id: str, hours: int = 24) -> list[dict[str, Any]]:
    """ดึงข้อมูล sensor ย้อนหลัง N ชั่วโมง — คืน list of dict"""
    flux = f"""
    from(bucket: "{settings.INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.device_id == "{device_id}")
      |> filter(fn: (r) => r._field == "pm2_5" or r._field == "aqi"
                        or r._field == "temperature" or r._field == "humidity")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    """
    tables = get_query_api().query(flux, org=settings.INFLUX_ORG)
    rows = []
    for table in tables:
        for record in table.records:
            rows.append({
                "timestamp":   record.get_time().isoformat(),
                "pm2_5":       record.values.get("pm2_5"),
                "aqi":         record.values.get("aqi"),
                "temperature": record.values.get("temperature"),
                "humidity":    record.values.get("humidity"),
            })
    return rows


def query_latest(device_id: str) -> dict[str, Any] | None:
    """ดึงค่าล่าสุดของ device"""
    flux = f"""
    from(bucket: "{settings.INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.device_id == "{device_id}")
      |> last()
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """
    tables = get_query_api().query(flux, org=settings.INFLUX_ORG)
    for table in tables:
        for record in table.records:
            return {
                "timestamp":   record.get_time().isoformat(),
                "pm2_5":       record.values.get("pm2_5"),
                "pm10":        record.values.get("pm10"),
                "aqi":         record.values.get("aqi"),
                "temperature": record.values.get("temperature"),
                "humidity":    record.values.get("humidity"),
                "pressure":    record.values.get("pressure"),
            }
    return None


def query_daily_avg(device_id: str, days: int = 7) -> list[dict]:
    """ค่าเฉลี่ย PM2.5 รายวัน (สำหรับ chart)"""
    flux = f"""
    from(bucket: "{settings.INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.device_id == "{device_id}")
      |> filter(fn: (r) => r._field == "pm2_5")
      |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
      |> yield(name: "daily_avg")
    """
    tables = get_query_api().query(flux, org=settings.INFLUX_ORG)
    rows = []
    for table in tables:
        for record in table.records:
            rows.append({
                "date":  record.get_time().strftime("%Y-%m-%d"),
                "pm2_5": round(record.get_value(), 2),
            })
    return rows
