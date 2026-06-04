import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from influxdb_client import Point
from typing import List, Dict, Any
from app.schemas import WeatherPoint
from app.influx import query as influx_query
from app.influx import write_point as influx_write_point
from app.config import (
    INFLUXDB_BUCKET,
    INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT as digital_twin_deleted_meas,
    INFLUXDB_MEASUREMENT as meas,
    INFLUXDB_MEASUREMENT2 as digital_twin_command_meas,
)


router = APIRouter(prefix="")


def _safe_flux_string(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _normalize_key(value: str) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _coerce_json(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def _flatten_dict(value: Any, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    value = _coerce_json(value)
    if not isinstance(value, dict):
        return flattened

    for key, raw_value in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        parsed_value = _coerce_json(raw_value)
        if isinstance(parsed_value, dict):
            flattened.update(_flatten_dict(parsed_value, path))
        else:
            flattened[path] = parsed_value
    return flattened


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(row)
    for key, value in row.items():
        if isinstance(value, dict) or (isinstance(value, str) and value.strip().startswith("{")):
            for nested_key, nested_value in _flatten_dict(value, key).items():
                flattened[nested_key] = nested_value
    return flattened


def _value_from(row: dict[str, Any], names: list[str]) -> Any:
    if not row:
        return None

    flattened = _flatten_row(row)
    normalized_names = {_normalize_key(name) for name in names}
    for key, value in flattened.items():
        if _normalize_key(key) in normalized_names:
            return value

    for key, value in flattened.items():
        normalized_key = _normalize_key(key)
        if any(normalized_key.endswith(name) for name in normalized_names):
            return value
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "accepted"}


def _same_value(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return str(left).strip() == str(right).strip()


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def _query_measurement_rows(measurement: str, minutes: int, limit: int) -> list[dict[str, Any]]:
    measurement = _safe_flux_string(measurement)
    flux = f'''
from(bucket: "{_safe_flux_string(INFLUXDB_BUCKET)}")
  |> range(start: -{minutes}m)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})
'''
    tables = influx_query(flux)
    rows: list[dict[str, Any]] = []

    for table in tables:
        for record in table.records:
            values = {
                key: value
                for key, value in record.values.items()
                if key not in {"result", "table", "_start", "_stop"}
            }
            record_time = record.get_time()
            values["time"] = record_time.isoformat() if record_time else values.get("_time")
            rows.append(values)

    rows.sort(key=lambda row: str(row.get("time") or ""), reverse=True)
    return rows


def _query_deleted_digital_twin_ids(minutes: int) -> set[str]:
    rows = _query_measurement_rows(digital_twin_deleted_meas, minutes, 1000)
    deleted_ids: set[str] = set()

    for row in rows:
        alert_id = _value_from(row, ["alert_id"])
        if alert_id:
            deleted_ids.add(str(alert_id))

    return deleted_ids


def _device_from(row: dict[str, Any]) -> str:
    thing_id = _value_from(row, ["thingId", "thing_id"])
    device_id = _value_from(row, ["device_id", "deviceId", "attributes.device_id"])
    if device_id:
        return str(device_id)
    if thing_id and ":" in str(thing_id):
        return str(thing_id).rsplit(":", 1)[1]
    return str(thing_id or "unknown")


def _same_device(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_device = _device_from(left)
    right_device = _device_from(right)
    if left_device == "unknown" or right_device == "unknown":
        return False
    return _normalize_key(left_device) == _normalize_key(right_device)


def _row_matches_command_device(command: dict[str, Any], row: dict[str, Any]) -> bool:
    return _same_device(command, row)


def _row_is_at_or_after(row: dict[str, Any], timestamp: datetime | None) -> bool:
    row_time = _parse_datetime(row.get("time") or row.get("_time"))
    return timestamp is None or row_time is None or row_time >= timestamp


def _latest_rows_by_device(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        device_id = _device_from(row)
        if device_id == "unknown":
            continue

        key = _normalize_key(device_id)
        current = latest.get(key)
        if current is None or str(row.get("time") or "") > str(current.get("time") or ""):
            latest[key] = row

    return sorted(latest.values(), key=lambda row: str(row.get("time") or ""), reverse=True)


def _build_digital_twin_alert(
    command: dict[str, Any],
    sensor_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    digital_twin_sampling = _value_from(command, ["sampling_s", "sampling_rate_s"])
    requested_sampling_rate = _value_from(command, [
        "sampling_s",
        "sampling_rate_s",
        "desiredProperties.sampling_rate_s",
        "features.sensors.desiredProperties.sampling_rate_s",
    ])
    desired_alert_active = _value_from(command, [
        "alert_active",
        "desiredProperties.alert_active",
        "features.sensors.desiredProperties.alert_active",
    ])
    desired_threshold = _value_from(command, [
        "alert_threshold_temp",
        "desiredProperties.alert_threshold_temp",
        "features.sensors.desiredProperties.alert_threshold_temp",
    ])

    command_time = command.get("time") or command.get("_time")
    matching_sensor_rows = [
        row
        for row in sensor_rows
        if _row_matches_command_device(command, row)
    ]
    sensor_row = next(
        (
            row
            for row in matching_sensor_rows
            if _value_from(row, ["sampling_s", "sampling_rate_s"]) is not None
        ),
        matching_sensor_rows[0] if matching_sensor_rows else None,
    )
    gateway_sampling = _value_from(sensor_row or {}, ["sampling_s", "sampling_rate_s"])
    gateway_time = sensor_row.get("time") if sensor_row else None

    digital_twin_confirmed = _same_value(digital_twin_sampling, gateway_sampling)
    sampling_rate_updated = digital_twin_confirmed
    gateway_sampling_rate = gateway_sampling
    confirmation_source = "digital_twin_measurement" if digital_twin_confirmed else None

    status = "updated" if sampling_rate_updated else "pending"
    description = (
        f"Gateway sampling updated to the new sampling rate: {digital_twin_sampling} seconds."
        if sampling_rate_updated
        else (
            f"Digital twin sampling is {digital_twin_sampling} seconds, but gateway telemetry "
            f"reports {gateway_sampling if gateway_sampling is not None else 'no current'} sampling_s. "
            "The gateway may be out of reach or without internet."
        )
    )

    device_id = _device_from(command)

    return {
        "id": f"digital-twin-{device_id}-{command_time}-{digital_twin_sampling}",
        "source": "digital_twin",
        "alert_type": "warning" if sampling_rate_updated else "critical",
        "device_id": device_id,
        "thingId": _value_from(command, ["thingId", "thing_id"]),
        "time": command_time,
        "delete_time": command_time,
        "ack_time": gateway_time or command_time,
        "sensor_time": gateway_time,
        "status": status,
        "confirmation_source": confirmation_source,
        "gateway_sampling_rate": gateway_sampling_rate,
        "digital_twin_sampling_rate": digital_twin_sampling,
        "sampling_comparison": {
            "digital_twin_device_id": device_id,
            "gateway_device_id": _device_from(sensor_row or {}) if sensor_row else None,
            "digital_twin_sampling_s": digital_twin_sampling,
            "gateway_sampling_s": gateway_sampling,
            "matched": sampling_rate_updated,
        },
        "gateway_measurement": sensor_row,
        "gateway_measurement_time": gateway_time,
        "description": description,
        "desired_properties": {
            "sampling_rate_s": requested_sampling_rate,
            "sampling_s": digital_twin_sampling,
            "revision": _value_from(command, ["revision"]),
            "alert_active": desired_alert_active,
            "alert_threshold_temp": desired_threshold,
        },
        "acknowledgement": command,
        "digital_twin_measurement": command,
        "change_for_alert": [
            {
                "parameter": "sampling_rate_s",
                "previous_value": None,
                "current_value": digital_twin_sampling,
                "ack_value": digital_twin_sampling,
                "sensor_value": gateway_sampling,
                "updated": sampling_rate_updated,
            },
            {
                "parameter": "alert_active",
                "previous_value": None,
                "current_value": desired_alert_active,
            },
            {
                "parameter": "alert_threshold_temp",
                "previous_value": None,
                "current_value": desired_threshold,
            },
        ],
    }


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


@router.get("/digital-twin/alerts")
def get_digital_twin_alerts(
    limit: int = Query(50, ge=1, le=200),
    minutes: int = Query(24 * 60, ge=1, le=7 * 24 * 60),
):
    try:
        command_rows = _latest_rows_by_device(_query_measurement_rows(digital_twin_command_meas, minutes, limit * 5))
        sensor_rows = _latest_rows_by_device(_query_measurement_rows(meas, minutes, limit * 5))
        deleted_alert_ids = _query_deleted_digital_twin_ids(7 * 24 * 60)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load digital twin alerts: {exc}") from exc

    alerts = [
        alert
        for command in command_rows
        for alert in [_build_digital_twin_alert(command, sensor_rows)]
        if _value_from(command, ["sampling_s", "sampling_rate_s"]) is not None
        and alert["id"] not in deleted_alert_ids
    ]
    return alerts[:limit]


@router.delete("/digital-twin/alerts/{alert_id:path}")
def delete_digital_twin_alert(
    alert_id: str,
    time: str = Query(..., description="Command timestamp returned by /digital-twin/alerts"),
    device_id: str | None = Query(None),
):
    if not _parse_datetime(time):
        raise HTTPException(status_code=400, detail="A valid alert time is required to delete the digital twin alert")

    try:
        point = (
            Point(digital_twin_deleted_meas)
            .tag("alert_id", alert_id)
            .tag("device_id", device_id or "unknown")
            .field("deleted", True)
            .field("alert_time", time)
            .time(datetime.now(UTC))
        )
        influx_write_point(point)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to mark digital twin alert deleted in InfluxDB: {exc}") from exc

    return {
        "deleted": True,
        "id": alert_id,
        "time": time,
        "device_id": device_id,
        "measurement": digital_twin_deleted_meas,
    }
