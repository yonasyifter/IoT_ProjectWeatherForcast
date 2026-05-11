"""
crew/src/crew.py

Smart Park AI Crew — multi-agent pipeline with RCMS Edge OpenAPI integration.

Architecture:
  - sensor_agent      : validates InfluxDB / device_data payload
  - edge_device_agent : queries RCMS OpenAPI (rcmsapi.js services equivalent)
  - context_agent     : builds multilingual context from both data sources
  - anomaly_agent     : detects anomalies and produces diagnostic findings
  - report_agent      : composes full Markdown report (used in report mode)
  - reasoning_agent   : answers conversational queries

Two modes:
  run_crew(...)        -> conversational answer (text or chart JSON)
  run_crew_report(...) -> full Markdown report for PDF/Word export
"""

import os
import sys
import json
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

# InfluxDB optional
try:
    from influx import query as influx_query
    from config import INFLUXDB_BUCKET
    _INFLUX_AVAILABLE = bool(INFLUXDB_BUCKET)
except Exception:
    influx_query = None
    INFLUXDB_BUCKET = ""
    _INFLUX_AVAILABLE = False

from .llm_router import call_llm
from .tools.sensor_tool import SensorDataTool
from .tools.rcmsapi_tool import (
    fetch_full_edge_snapshot,
    RCMS_EDGE_URL,
)

_sensor_parser = SensorDataTool()

CONVERSATIONAL_SYSTEM_PROMPT = """\
You are the Smart Park AI Analyst, an expert in IoT environmental monitoring
and Edge device management. You help park administrators understand sensor data,
device health, spot anomalies, and get concise answers about park conditions.

You have access to two data sources:
1. Sensor telemetry (InfluxDB / live device payload) - temperature, humidity,
   pressure, noise, TOF, light, weather prediction.
2. RCMS Edge OpenAPI - device inventory, firmware versions, system resources
   (CPU, RAM, storage), connectivity status, active alerts, diagnostics.

Rules:
- Always respond in the language specified. Never switch languages.
- Never fabricate sensor readings or device data. If data is missing, say so.
- For chart/graph/visualization requests, output ONLY a JSON block like:
  ```json
  {"chart_type":"bar","title":"...","labels":[...],"data":[...],"unit":"...","description":"..."}
  ```
  Supported chart_type: bar, line, pie, doughnut, radar
  For multi-series use "datasets":[{"label":"...","data":[...]},...]
- For device queries, always include: device ID, model, firmware, status, uptime
  when available from the RCMS Edge snapshot.
- For all other queries: 2-4 sentences, warm conversational tone, include units.
- Never mix chart JSON with plain text. Output exactly one format.
"""

REPORT_SYSTEM_PROMPT = """\
You are the Smart Park Report Composer. Your task is to produce a comprehensive,
professional Markdown analysis report for park administrators.

The report must be well-structured, accurate, and suitable for PDF or Word export.
Include all sections: executive summary, device inventory, environmental conditions,
weather assessment, system health, anomalies/alerts, and actionable recommendations.

Rules:
- Use proper Markdown: ## headings, | tables |, **bold**, bullet lists.
- All sensor values must include units (C, %, Pa, dB, cm, etc.).
- All device data must include firmware version, model, uptime, and status.
- Never fabricate readings. If a data source is unavailable, state it clearly.
- Respond exclusively in the language specified.
- Be thorough - this report will be exported and shared with stakeholders.
"""


def _query_influx_summary() -> str:
    if not _INFLUX_AVAILABLE or not influx_query:
        return ""
    try:
        flux = (
            f'from(bucket:"{INFLUXDB_BUCKET}")'
            "|> range(start: -1h)"
            "|> filter(fn: (r) => r._measurement == r._measurement)"
            "|> last()"
        )
        tables = influx_query(flux)
        rows = []
        for table in tables:
            for rec in table.records:
                rows.append(
                    f"{rec.get_field()}={rec.get_value()} "
                    f"(device={rec.values.get('device_id','?')} "
                    f"time={rec.get_time().isoformat()})"
                )
                if len(rows) >= 40:
                    break
        return "\n".join(rows) if rows else ""
    except Exception as exc:
        print(f"[CREW] InfluxDB query skipped: {exc}")
        return ""


def _fetch_rcms_snapshot_str() -> str:
    try:
        snapshot = fetch_full_edge_snapshot()
        return json.dumps(snapshot, indent=2, default=str)
    except Exception as exc:
        return json.dumps({"error": f"RCMS snapshot failed: {exc}"})


def _build_messages(
    device_data: str,
    user_query: str,
    language: str,
    context_data: str,
    mode: str = "chat",
) -> list:
    parsed_sensors = _sensor_parser._run(device_data or "null")
    influx_summary = _query_influx_summary()
    rcms_snapshot  = _fetch_rcms_snapshot_str()

    parts = [
        f"Language: {language}",
        f"Query: {user_query}",
        f"Mode: {mode}",
        f"Timestamp: {datetime.datetime.utcnow().isoformat()}Z",
        "",
        "=== Current Sensor Readings (InfluxDB / Device Payload) ===",
        parsed_sensors,
    ]

    if influx_summary:
        parts += ["", "=== Recent InfluxDB History (last 1h) ===", influx_summary]

    parts += [
        "",
        "=== RCMS Edge Device OpenAPI Snapshot ===",
        f"(Edge URL: {RCMS_EDGE_URL})",
        rcms_snapshot,
    ]

    if context_data:
        parts += ["", "=== Admin Context ===", context_data]

    if mode == "report":
        parts += [
            "",
            "=== Report Instructions ===",
            "Generate a full Markdown analysis report covering ALL sections: "
            "executive summary, device inventory table, environmental conditions, "
            "weather assessment, system health (CPU/RAM/storage), anomaly findings "
            "with severity levels, and a numbered recommendations list. "
            "Be thorough. This report will be exported to PDF or Word.",
        ]

    system_prompt = REPORT_SYSTEM_PROMPT if mode == "report" else CONVERSATIONAL_SYSTEM_PROMPT

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": "\n".join(parts)},
    ]


def run_crew(
    device_data: str,
    user_query: str,
    language: str = "en",
    context_data: str = "",
) -> str:
    messages = _build_messages(
        device_data=device_data,
        user_query=user_query,
        language=language,
        context_data=context_data,
        mode="chat",
    )
    return call_llm(messages, timeout=55)


def run_crew_report(
    device_data: str,
    user_query: str,
    language: str = "en",
    context_data: str = "",
) -> str:
    messages = _build_messages(
        device_data=device_data,
        user_query=user_query,
        language=language,
        context_data=context_data,
        mode="report",
    )
    return call_llm(messages, timeout=90)