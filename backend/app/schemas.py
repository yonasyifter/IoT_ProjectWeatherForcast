from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Any, Optional, List

class WeatherPoint(BaseModel):
    time: Optional[datetime] = None
    device_id: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    light: Optional[float] = None
    noise: Optional[float] = None
    tof: Optional[float] = None
    angle: Optional[float] = None
    accX: Optional[float] = None
    accY: Optional[float] = None
    accZ: Optional[float] = None
    vibrAccX: Optional[float] = None
    vibrAccY: Optional[float] = None
    vibrAccZ: Optional[float] = None
    noise_condition: Optional[str] = None
    weather_prediction: Optional[str] = None
    prediction_confidence: Optional[float] = None
    latitude:Optional[float]=None
    longitude:Optional[float]=None
    GPS_status: Optional[str] = None
    EG5120_CPU_Temprature: Optional[float] = None
    EG5120_CPU_status: Optional[str] = None
    EG5120_Storage_total: Optional[str] = None
    EG5120_Storage_free: Optional[str] = None
    EG5120_RAM_total_mb: Optional[int] = None
    EG5120_RAM_free_mb: Optional[int] = None
    prediction_time: Optional[float] = None


class AlertChange(BaseModel):
    parameter: str
    previous_value: Any = None
    current_value: Any = None


class WeatherAlertIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    alert_type: str = Field(..., description="warning or Critical")
    change_for_alert: List[AlertChange]
    device_id: str = Field(..., min_length=1, description="Device that produced the alert")
    description: Optional[str] = None
    time: Optional[datetime] = None
    measurement: Optional[str] = None

    @field_validator("alert_type")
    @classmethod
    def normalize_alert_type(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"warning", "critical"}:
            raise ValueError("alert_type must be warning or Critical")
        return normalized

    @field_validator("change_for_alert", mode="before")
    @classmethod
    def normalize_changes(cls, value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            if "parameter" in value:
                return [value]

            changes = []
            for parameter, change in value.items():
                if isinstance(change, dict):
                    changes.append({"parameter": parameter, **change})
                else:
                    changes.append({"parameter": parameter, "current_value": change})
            return changes
        raise ValueError("change_for_alert must be an object or a list of objects")

    @field_validator("device_id")
    @classmethod
    def normalize_device_id(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("device_id is required")
        return normalized


class WeatherAlert(WeatherAlertIn):
    id: str
    created_at: datetime
