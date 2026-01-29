from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WeatherPoint(BaseModel):
    time: Optional[datetime] = None
    device_id: Optional[int] = None
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
    forcast: Optional[str] = None
    latitude:Optional[float]=None
    longitude:Optional[float]=None
