from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

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
