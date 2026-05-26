import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.schemas import WeatherAlert, WeatherAlertIn, WeatherPoint
from app.influx import query as influx_query
from app.config import INFLUXDB_BUCKET, INFLUXDB_MEASUREMENT as meas


router = APIRouter(prefix="")
ALERTS_FILE = Path(__file__).resolve().parents[1] / "data" / "weather_alerts.json"


def _load_alerts() -> list[dict[str, Any]]:
    if not ALERTS_FILE.exists():
        return []
    with ALERTS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_alerts(alerts: list[dict[str, Any]]) -> None:
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(alerts, file, ensure_ascii=False, indent=2)


def _has_device_id(alert: dict[str, Any]) -> bool:
    device_id = alert.get("device_id")
    return device_id is not None and str(device_id).strip() != ""


@router.get("/forecast/", response_model=List[WeatherPoint])
def get_weather_forecast(
    # device_id: str,
    minutes: int = Query(60, ge=1, le=7*24*60),
        measurement: str = Query(meas),):
    # Flux query: filter by time range, measurement, and device_id tag
    flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{minutes}m)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> keep(columns: ["_time","_field","_value","device_id"])
'''

    tables = influx_query(flux)

    # Influx results are "tall": each record is (time, device_id, field, value).
    # We reshape into "wide" JSON: one object per time/device pair.
    by_time_device: Dict[tuple[str, str], Dict[str, Any]] = {}

    for table in tables:
        for record in table.records:
            t = record.get_time().isoformat()
            device_id = str(record.values.get("device_id", "unknown"))
            field = record.get_field()
            value = record.get_value()
            key = (t, device_id)

            if key not in by_time_device:
                by_time_device[key] = {"time": record.get_time(), "device_id": device_id}
            by_time_device[key][field] = value

    # Convert dict->list, sort by time ascending
    result = list(by_time_device.values())
    result.sort(key=lambda x: x["time"])
    return result


@router.put("/alert", response_model=WeatherAlert)
def put_weather_alert(payload: WeatherAlertIn):
    data = payload.model_dump()
    data["time"] = payload.time or datetime.now(UTC)
    alert = WeatherAlert(
        **data,
        id=uuid4().hex,
        created_at=datetime.now(UTC),
    )

    alerts = [alert for alert in _load_alerts() if _has_device_id(alert)]
    alerts.insert(0, alert.model_dump(mode="json"))
    _save_alerts(alerts[:500])
    return alert


@router.get("/alert", response_model=List[WeatherAlert])
def get_weather_alerts(
    limit: int = Query(50, ge=1, le=500),
    alert_type: str | None = Query(None, pattern="^(warning|critical|Critical)$"),
):
    alerts = [alert for alert in _load_alerts() if _has_device_id(alert)]
    if alert_type:
        normalized = alert_type.lower()
        alerts = [alert for alert in alerts if alert.get("alert_type") == normalized]
    return alerts[:limit]


@router.delete("/alert/{alert_id}")
def delete_weather_alert(alert_id: str):
    alerts = _load_alerts()
    remaining_alerts = [alert for alert in alerts if alert.get("id") != alert_id]

    if len(remaining_alerts) == len(alerts):
        raise HTTPException(status_code=404, detail="Alert not found")

    _save_alerts(remaining_alerts)
    return {"deleted": True, "id": alert_id}
