from fastapi import APIRouter, Query
from typing import List, Dict, Any
from app.schemas import WeatherPoint
from app.influx import query as influx_query
from app.config import INFLUXDB_BUCKET, INFLUXDB_MEASUREMENT as meas


router = APIRouter(prefix="")


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
