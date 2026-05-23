"""

RCMS OpenAPI Edge Device Tool
Fetches live device data from the Edge device via its OpenAPI (rcmsapi.js-compatible)
REST endpoints. This mirrors the services defined in rcmsapi.js on the admin-side.

Endpoints covered:
  GET /api/v1/devices          — list all registered Edge devices
  GET /api/v1/devices/{id}     — device detail (model, firmware, status, uptime)
  GET /api/v1/devices/{id}/sensors  — per-device sensor readings
  GET /api/v1/devices/{id}/status   — connectivity / health status
  GET /api/v1/system/info      — Edge system info (CPU, RAM, storage)
  GET /api/v1/system/network   — network interfaces and IP config
  GET /api/v1/alerts           — active alert list
  GET /api/v1/diagnostics      — self-diagnostic report

All calls are best-effort: if the Edge is offline, each method returns
a structured error dict so the crew can still respond gracefully.
"""

import json
import os
import logging
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from crewai.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)

# Base URL of the Edge device OpenAPI.  Set RCMS_EDGE_URL in .env.
# Falls back to localhost for local dev / Docker compose networks.
RCMS_EDGE_URL = os.getenv("RCMS_EDGE_URL", "http://localhost:8081").rstrip("/")
RCMS_API_KEY  = os.getenv("RCMS_API_KEY", "")          # optional Bearer token
RCMS_TIMEOUT  = int(os.getenv("RCMS_TIMEOUT_SECONDS", "6"))


def _get(path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Internal helper: GET from RCMS Edge and return parsed JSON or error dict."""
    url = f"{RCMS_EDGE_URL}{path}"
    headers = {"Accept": "application/json"}
    if RCMS_API_KEY:
        headers["Authorization"] = f"Bearer {RCMS_API_KEY}"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=RCMS_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "RCMS Edge device unreachable", "url": url}
    except requests.exceptions.Timeout:
        return {"error": f"RCMS Edge device timed out after {RCMS_TIMEOUT}s", "url": url}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"HTTP {exc.response.status_code}", "url": url}
    except Exception as exc:
        return {"error": str(exc), "url": url}


# ── Individual service functions (mirrors rcmsapi.js services section) ────────

def fetch_all_devices() -> Dict[str, Any]:
    """GET /api/v1/devices — list every registered Edge device."""
    return _get("/api/v1/devices")


def fetch_device_info(device_id: str) -> Dict[str, Any]:
    """GET /api/v1/devices/{id} — model, firmware, serial, status, uptime."""
    return _get(f"/api/v1/devices/{device_id}")


def fetch_device_sensors(device_id: str) -> Dict[str, Any]:
    """GET /api/v1/devices/{id}/sensors — latest sensor readings for one device."""
    return _get(f"/api/v1/devices/{device_id}/sensors")


def fetch_device_status(device_id: str) -> Dict[str, Any]:
    """GET /api/v1/devices/{id}/status — connectivity and health status."""
    return _get(f"/api/v1/devices/{device_id}/status")


def fetch_system_info() -> Dict[str, Any]:
    """GET /api/v1/system/info — Edge CPU, RAM, storage, OS, uptime."""
    return _get("/api/v1/system/info")


def fetch_system_network() -> Dict[str, Any]:
    """GET /api/v1/system/network — network interfaces, IPs, MAC addresses."""
    return _get("/api/v1/system/network")


def fetch_active_alerts() -> Dict[str, Any]:
    """GET /api/v1/alerts — list of active alert conditions on the Edge."""
    return _get("/api/v1/alerts")


def fetch_diagnostics() -> Dict[str, Any]:
    """GET /api/v1/diagnostics — self-diagnostic report (sensor health, errors)."""
    return _get("/api/v1/diagnostics")


def fetch_full_edge_snapshot() -> Dict[str, Any]:
    """
    Aggregate helper: fetches system info, all devices, alerts, and diagnostics
    in one call.  Returns a consolidated dict suitable for LLM context.
    """
    # 1. Fetch the base device list first (needed for enrichment)
    devices_raw = fetch_all_devices()
    devices = devices_raw if isinstance(devices_raw, list) else devices_raw.get("devices", devices_raw)

    enriched_devices = []
    if isinstance(devices, list):
        # Limit to 10 devices to avoid huge prompts
        target_devices = devices[:10]

        # Parallelize enrichment: fetch sensors and status for each device
        with ThreadPoolExecutor() as executor:
            # Create a map of future -> (device, type)
            future_to_data = {}
            for dev in target_devices:
                dev_id = str(dev.get("id") or dev.get("device_id", ""))
                if dev_id:
                    # Fetch sensors
                    future_to_data[executor.submit(fetch_device_sensors, dev_id)] = (dev, "sensors")
                    # Fetch status
                    future_to_data[executor.submit(fetch_device_status, dev_id)] = (dev, "status")

            for future in as_completed(future_to_data):
                dev, data_type = future_to_data[future]
                try:
                    result = future.result()
                    dev[data_type] = result
                except Exception as exc:
                    dev[data_type] = {"error": str(exc)}

        enriched_devices = target_devices

    # 2. Parallelize system-level fetches
    system_tasks = {
        "system_info": fetch_system_info,
        "network":     fetch_system_network,
        "alerts":      fetch_active_alerts,
        "diagnostics": fetch_diagnostics,
    }

    system_results = {}
    with ThreadPoolExecutor() as executor:
        future_to_task = {executor.submit(fn): name for name, fn in system_tasks.items()}
        for future in as_completed(future_to_task):
            name = future_to_task[future]
            try:
                system_results[name] = future.result()
            except Exception as exc:
                system_results[name] = {"error": str(exc)}

    return {
        **system_results,
        "devices": enriched_devices,
    }


# ── CrewAI Tool wrappers ───────────────────────────────────────────────────────

class RCMSDeviceListTool(BaseTool):
    name: str = "rcms_device_list"
    description: str = (
        "Fetches the list of all Edge devices registered on the RCMS platform. "
        "Returns device IDs, names, models, and connectivity status. "
        "Use this to discover which devices are available before querying details."
    )

    def _run(self, _input: str = "") -> str:
        result = fetch_all_devices()
        return json.dumps(result, indent=2, default=str)


class RCMSDeviceInfoTool(BaseTool):
    name: str = "rcms_device_info"
    description: str = (
        "Fetches detailed information about a specific Edge device by its ID. "
        "Returns model, firmware version, serial number, uptime, and operational status. "
        "Input: the device_id string (e.g. 'device-001')."
    )

    def _run(self, device_id: str) -> str:
        result = fetch_device_info(device_id.strip())
        return json.dumps(result, indent=2, default=str)


class RCMSDeviceSensorsTool(BaseTool):
    name: str = "rcms_device_sensors"
    description: str = (
        "Fetches the latest sensor readings from a specific Edge device. "
        "Returns temperature, humidity, pressure, noise, TOF, light, and location data. "
        "Input: the device_id string."
    )

    def _run(self, device_id: str) -> str:
        result = fetch_device_sensors(device_id.strip())
        return json.dumps(result, indent=2, default=str)


class RCMSSystemInfoTool(BaseTool):
    name: str = "rcms_system_info"
    description: str = (
        "Fetches Edge system-level information: CPU usage, RAM, storage, OS version, "
        "kernel, and system uptime. Use to assess overall Edge health and resources."
    )

    def _run(self, _input: str = "") -> str:
        result = fetch_system_info()
        return json.dumps(result, indent=2, default=str)


class RCMSAlertsTool(BaseTool):
    name: str = "rcms_active_alerts"
    description: str = (
        "Fetches the current list of active alerts from the RCMS Edge. "
        "Returns alert type, severity, affected device, and timestamp. "
        "Use to identify ongoing issues or anomalies in the park network."
    )

    def _run(self, _input: str = "") -> str:
        result = fetch_active_alerts()
        return json.dumps(result, indent=2, default=str)


class RCMSFullSnapshotTool(BaseTool):
    name: str = "rcms_full_snapshot"
    description: str = (
        "Fetches a comprehensive snapshot of the entire RCMS Edge: system info, "
        "network config, all devices with their sensor readings and status, "
        "active alerts, and diagnostics. Use when a broad overview is needed "
        "or when generating a full system report."
    )

    def _run(self, _input: str = "") -> str:
        result = fetch_full_edge_snapshot()
        return json.dumps(result, indent=2, default=str)


# Singleton instances for import
rcms_device_list_tool    = RCMSDeviceListTool()
rcms_device_info_tool    = RCMSDeviceInfoTool()
rcms_device_sensors_tool = RCMSDeviceSensorsTool()
rcms_system_info_tool    = RCMSSystemInfoTool()
rcms_alerts_tool         = RCMSAlertsTool()
rcms_full_snapshot_tool  = RCMSFullSnapshotTool()