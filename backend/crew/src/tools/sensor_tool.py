"""
crew/src/tools/sensor_tool.py

Sensor data processing tool for CrewAI agents.
Parses and validates raw IoT sensor JSON from the park's device network.
"""

import json
from typing import Any
from crewai.tools import BaseTool
from pydantic import Field


SUPPORTED_METRICS = [
    "temperature", "humidity", "pressure", "light",
    "noise", "tof", "latitude", "longitude",
    "weather_prediction", "prediction_confidence", "time", "device_id"
]


class SensorDataTool(BaseTool):
    """Parse and validate raw IoT sensor JSON data."""

    name: str = "sensor_data_parser"
    description: str = (
        "Parses and validates raw IoT sensor JSON data from the Smart Park device network. "
        "Returns a structured summary of available devices and their readings."
    )

    def _run(self, device_data: str) -> str:
        if not device_data or device_data.strip() in ("", "null", "None"):
            return json.dumps({"status": "no_data", "devices": [], "weather": None})

        try:
            data = json.loads(device_data)
        except json.JSONDecodeError as e:
            return json.dumps({"status": "parse_error", "error": str(e), "devices": []})

        if not isinstance(data, list):
            return json.dumps({"status": "invalid_format", "devices": []})

        devices = []
        weather_prediction = None
        prediction_confidence = None

        for item in data:
            if not isinstance(item, dict):
                continue

            device: dict[str, Any] = {
                "device_id": item.get("device_id", "unknown")
            }

            # Core environmental metrics
            for metric in ["temperature", "humidity", "pressure", "light",
                           "noise", "tof", "latitude", "longitude", "time"]:
                if metric in item:
                    device[metric] = item[metric]

            # Weather prediction (park-wide — take first occurrence)
            if "weather_prediction" in item and weather_prediction is None:
                weather_prediction = item["weather_prediction"]
                prediction_confidence = float(item.get("prediction_confidence", 0))

            devices.append(device)

        return json.dumps({
            "status": "ok",
            "device_count": len(devices),
            "devices": devices,
            "weather": {
                "prediction": weather_prediction,
                "confidence_pct": prediction_confidence
            } if weather_prediction else None
        }, indent=2)


# Singleton instance for import
sensor_tool = SensorDataTool()
