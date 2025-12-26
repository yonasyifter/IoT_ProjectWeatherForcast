from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WeatherPoint(BaseModel):
    time: datetime
    device_id: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None