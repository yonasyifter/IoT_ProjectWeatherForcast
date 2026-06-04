"""
crew/src/crew.py  —  Smart Park AI Crew  v3.0
Della Silla Smart Park IoT Platform

Architecture
────────────
Two public entry points:

  run_crew(...)        → conversational answer (text | LaTeX | chart JSON)
  run_crew_report(...) → full Markdown report with delivery prompt

Pipeline (both modes share the same message-build path):

  ┌─────────────────────────────────────────────────────────────────┐
  │  Data layer  (fetched once, reused across agents)               │
  │  ┌──────────────────┐  ┌───────────────────────────────────┐   │
  │  │  SensorDataTool  │  │  RCMS EG5120 fetch_full_snapshot  │   │
  │  │  (JSON payload)  │  │  (OpenAPI: devices, alerts, sys)  │   │
  │  └────────┬─────────┘  └──────────────────┬────────────────┘   │
  │           │                               │                    │
  │           ▼                               ▼                    │
  │      Parsed sensors               RCMS snapshot JSON           │
  │           │                               │                    │
  │           └───────────┬───────────────────┘                    │
  │                       ▼                                        │
  │             InfluxDB recent history (optional)                  │
  └───────────────────────┬─────────────────────────────────────────┘
                          │
                          ▼
             Real CrewAI sequential crew
             Agents + Tasks loaded from config/*.yaml

The agents and tasks in config/agents.yaml and config/tasks.yaml are now
runtime CrewAI objects. The data layer still fetches deterministic context
once before the crew starts, then injects it into the YAML-driven tasks.

Data sources
────────────
1. InfluxDB         — time-series telemetry (query_influx_summary)
2. RCMS EG5120 OpenAPI — edge device management (fetch_full_snapshot)
3. Firebase         — auth / Firestore config (status injected by router)
4. device_data      — JSON payload forwarded from the frontend
5. Site operations  — backend/API capability catalog, digital-twin alerts,
                      emergency requests, and planned/available actions
6. LLM general knowledge — fallback when official data is missing
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from urllib import request as urlrequest
from urllib import error as urlerror
from pathlib import Path

import yaml
from crewai import Agent, Crew, LLM, Process, Task

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

# ── InfluxDB (optional) ───────────────────────────────────────────────────────
try:
    from influx import query as influx_query
    from config import (
        INFLUXDB_BUCKET,
        INFLUXDB_MEASUREMENT,
        INFLUXDB_MEASUREMENT2,
        INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT,
    )
    _INFLUX_AVAILABLE = bool(INFLUXDB_BUCKET)
except Exception:
    influx_query = None          # type: ignore[assignment]
    INFLUXDB_BUCKET = ""
    INFLUXDB_MEASUREMENT = ""
    INFLUXDB_MEASUREMENT2 = "digitalTwinCommand"
    INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT = "DeletedDigitalTwinAlert"
    _INFLUX_AVAILABLE = False

# ── Local modules ─────────────────────────────────────────────────────────────
from .llm_router import PROVIDERS, _get_key
from .tools.sensor_tool import SensorDataTool
from .tools.influxdb_query_tool import InfluxDBQueryTool
from .tools.rcmsapi_tool import (
    RCMS_EDGE_URL,
    fetch_full_edge_snapshot,
    rcms_alerts_tool,
    rcms_device_info_tool,
    rcms_device_list_tool,
    rcms_device_sensors_tool,
    rcms_full_snapshot_tool,
    rcms_system_info_tool,
)

_sensor_parser = SensorDataTool()
_CONFIG_DIR = Path(__file__).resolve().parent / "config"

# ─────────────────────────────────────────────────────────────────────────────
# InfluxDB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _query_influx_summary(window: str = "1h") -> str:
    """
    Fetch recent InfluxDB readings. Returns a formatted string or "".
    window: any InfluxDB duration string e.g. "1h", "2h", "7d"
    """
    if not _INFLUX_AVAILABLE or not influx_query:
        return ""
    try:
        measurement_filter = (
            f'|> filter(fn: (r) => r._measurement == "{INFLUXDB_MEASUREMENT}")'
            if INFLUXDB_MEASUREMENT else ""
        )
        flux = (
            f'from(bucket:"{INFLUXDB_BUCKET}")'
            f"|> range(start: -{window})"
            f"{measurement_filter}"
            "|> filter(fn: (r) => "
            '   r._field == "temperature" or r._field == "humidity" or '
            '   r._field == "pressure"    or r._field == "noise"    or '
            '   r._field == "light"       or r._field == "tof")'
            "|> aggregateWindow(every: 5m, fn: mean, createEmpty: false)"
            "|> keep(columns: [\"_time\",\"_field\",\"_value\",\"device_id\"])"
        )
        tables = influx_query(flux)
        rows: list[str] = []
        for table in tables:
            for rec in table.records:
                ts  = rec.get_time()
                val = rec.get_value()
                fld = rec.get_field()
                dev = rec.values.get("device_id", "?")
                if ts is None or val is None:
                    continue
                try:
                    rows.append(
                        f"{fld}={round(float(val), 3)}"
                        f" device={dev}"
                        f" time={ts.isoformat()}"
                    )
                except (TypeError, ValueError):
                    continue
                if len(rows) >= 120:   # cap to avoid token explosion
                    break
            if len(rows) >= 120:
                break
        return "\n".join(rows) if rows else "(no InfluxDB records in window)"
    except Exception as exc:
        return f"(InfluxDB query failed: {exc})"


def _query_influx_range(field: str, window: str) -> str:
    """Targeted single-field InfluxDB query for specific analytics."""
    if not _INFLUX_AVAILABLE or not influx_query:
        return ""
    try:
        measurement_filter = (
            f'|> filter(fn: (r) => r._measurement == "{INFLUXDB_MEASUREMENT}")'
            if INFLUXDB_MEASUREMENT else ""
        )
        flux = (
            f'from(bucket:"{INFLUXDB_BUCKET}")'
            f"|> range(start: -{window})"
            f"{measurement_filter}"
            f'|> filter(fn: (r) => r._field == "{field}")'
            "|> keep(columns: [\"_time\",\"_value\",\"device_id\"])"
        )
        tables = influx_query(flux)
        rows: list[str] = []
        for table in tables:
            for rec in table.records:
                ts  = rec.get_time()
                val = rec.get_value()
                dev = rec.values.get("device_id", "?")
                if ts is None or val is None:
                    continue
                try:
                    rows.append(
                        f"device={dev}"
                        f" time={ts.isoformat()}"
                        f" {field}={round(float(val), 3)}"
                    )
                except (TypeError, ValueError):
                    continue
                if len(rows) >= 200:
                    break
        return "\n".join(rows) if rows else f"(no {field} data in window -{window})"
    except Exception as exc:
        return f"(InfluxDB {field} query failed: {exc})"


# ─────────────────────────────────────────────────────────────────────────────
# RCMS helper
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_rcms_snapshot() -> str:
    """Fetch and serialise the full RCMS EG5120 Edge snapshot."""
    try:
        snapshot = fetch_full_edge_snapshot()
        return json.dumps(snapshot, indent=2, default=str)
    except Exception as exc:
        return json.dumps({
            "error": f"RCMS snapshot failed: {exc}",
            "edge_status": "unreachable",
            "edge_url": RCMS_EDGE_URL,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Site-wide operations context
# ─────────────────────────────────────────────────────────────────────────────

_EMERGENCY_API_URL = os.getenv(
    "EMERGENCY_API_URL",
    "https://l6wlyfij89.execute-api.eu-north-1.amazonaws.com/prod/admin/emergency",
)


def _query_latest_measurement_rows(measurement: str, minutes: int = 1440, limit: int = 25) -> list[dict]:
    if not _INFLUX_AVAILABLE or not influx_query or not measurement:
        return []
    try:
        flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{minutes}m)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})
'''
        tables = influx_query(flux)
        rows: list[dict] = []
        for table in tables:
            for rec in table.records:
                values = {
                    key: value
                    for key, value in rec.values.items()
                    if key not in {"result", "table", "_start", "_stop"}
                }
                rec_time = rec.get_time()
                values["time"] = rec_time.isoformat() if rec_time else values.get("_time")
                rows.append(values)
        return rows[:limit]
    except Exception as exc:
        return [{"error": f"{measurement} query failed: {exc}"}]


def _safe_json_preview(value, limit: int = 12):
    if isinstance(value, list):
        return value[:limit]
    if isinstance(value, dict):
        return value
    return value


def _fetch_emergency_requests() -> dict:
    try:
        req = urlrequest.Request(_EMERGENCY_API_URL, method="GET")
        with urlrequest.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        payload = json.loads(raw) if raw else []
        requests = payload if isinstance(payload, list) else (
            payload.get("items")
            or payload.get("requests")
            or payload.get("emergencies")
            or payload.get("data")
            or []
        )
        if not isinstance(requests, list):
            requests = []
        return {
            "source": "Emergency API",
            "status": "ok",
            "active_request_count": len(requests),
            "active_requests_preview": _safe_json_preview(requests),
            "supported_actions": ["GET /api/emergency", "POST /api/emergency/resolve"],
        }
    except (OSError, ValueError, urlerror.URLError) as exc:
        return {
            "source": "Emergency API",
            "status": "unavailable",
            "error": str(exc),
            "active_request_count": None,
            "supported_actions": ["GET /api/emergency", "POST /api/emergency/resolve"],
        }


def _build_site_operations_snapshot() -> dict:
    command_rows = _query_latest_measurement_rows(INFLUXDB_MEASUREMENT2, limit=15)
    deleted_alert_rows = _query_latest_measurement_rows(INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT, minutes=7 * 24 * 60, limit=15)
    emergency = _fetch_emergency_requests()

    return {
        "purpose": (
            "Whole-site operational context for the AI agent/chatbot. Use this "
            "to answer what has been performed, what is currently happening, "
            "and what operations can be performed or are expected next."
        ),
        "backend_routes": {
            "weather_and_sensor_data": {
                "read_current_history": "GET /api/weather/forecast/?minutes=<1..10080>&measurement=<name>",
                "read_digital_twin_alerts": "GET /api/weather/digital-twin/alerts",
                "dismiss_digital_twin_alert": "DELETE /api/weather/digital-twin/alerts/{alert_id}?time=<timestamp>&device_id=<id>",
                "data_sources": [
                    INFLUXDB_MEASUREMENT,
                    INFLUXDB_MEASUREMENT2,
                    INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT,
                ],
            },
            "emergency": {
                "read_active_requests": "GET /api/emergency",
                "resolve_request": "POST /api/emergency/resolve",
                "upstream_source": _EMERGENCY_API_URL,
            },
            "rcms": {
                "proxy": "POST /api/rcms/request",
                "operations": [
                    "device inventory, detail, GPS, status, traffic, signal, syslog, alerts",
                    "add/delete device",
                    "set device group/description",
                    "reboot device",
                    "generate/push config file",
                    "query command status",
                ],
            },
            "ai": {
                "chat": "POST /api/crew/chat",
                "report": "POST /api/crew/report",
                "deliver_report": "POST /api/crew/deliver",
                "rag": "POST /api/rag/chat",
            },
            "auth": {
                "session_status": "GET /api/auth/session-status",
                "admin_guard": "Crew, RCMS, and protected dashboard actions require an authenticated admin session.",
            },
        },
        "frontend_pages": {
            "weather": "Weather map/current sensor readings from InfluxDB",
            "weather_alerts": "Digital-twin alert review and dismiss workflow",
            "emergency": "Active visitor emergency map and resolve workflow",
            "rcms_dashboard": "RCMS dashboard/inventory and network totals",
            "rcms_devices": "RCMS device management, reboot, config and metadata actions",
            "ai_agent": "CrewAI analysis, reports, charts, voice, PDF/Word delivery",
            "sensor_dashboard": "Sensor panels and charts",
        },
        "performed_or_recorded_operations": {
            "digital_twin_measurement2_preview": command_rows,
            "dismissed_digital_twin_alerts_preview": deleted_alert_rows,
            "emergency_requests": emergency,
        },
        "operation_state_meaning": {
            "performed": "confirmed measurement rows, resolved/dismissed alerts, sent RCMS commands, delivered reports",
            "performing": "pending digital-twin commands, active emergency requests, current sensor/RCMS state",
            "going_to_be_performed": "available next actions exposed by the site routes and UI controls",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Detect requested time window from the query string
# ─────────────────────────────────────────────────────────────────────────────

import re as _re

_WINDOW_PATTERNS: list[tuple[_re.Pattern, str]] = [
    (_re.compile(r"\b(\d{1,3})\s*hour", _re.I),  lambda m: f"{m.group(1)}h"),
    (_re.compile(r"\b(\d{1,3})\s*h\b",  _re.I),  lambda m: f"{m.group(1)}h"),
    (_re.compile(r"\b(\d{1,3})\s*day",  _re.I),  lambda m: f"{m.group(1)}d"),
    (_re.compile(r"\b(\d{1,3})\s*week", _re.I),  lambda m: f"{int(m.group(1))*7}d"),
    (_re.compile(r"\btoday\b",          _re.I),  lambda m: "24h"),
    (_re.compile(r"\bthis week\b",      _re.I),  lambda m: "7d"),
    (_re.compile(r"\bthis month\b",     _re.I),  lambda m: "30d"),
]

def _detect_window(query: str) -> str:
    """Return an InfluxDB duration string from natural language, default 1h."""
    for pattern, builder in _WINDOW_PATTERNS:
        m = pattern.search(query)
        if m:
            return builder(m)
    return "1h"


# ─────────────────────────────────────────────────────────────────────────────
# Runtime context — shared by both chat and report crews
# ─────────────────────────────────────────────────────────────────────────────

def _build_runtime_inputs(
    device_data: str,
    user_query: str,
    language: str,
    context_data: str,
    mode: str = "chat",  # "chat" | "report"
) -> dict:
    now_utc = datetime.datetime.utcnow().isoformat() + "Z"
    window   = _detect_window(user_query)

    # ── Data fetches ──────────────────────────────────────────────────────────
    parsed_sensors  = _sensor_parser._run(device_data or "null")
    influx_general  = _query_influx_summary(window=window)
    rcms_snapshot   = _fetch_rcms_snapshot()
    site_operations = _build_site_operations_snapshot()

    # If query targets a specific metric, fetch a targeted range too
    targeted_data = ""
    for metric in ("temperature", "humidity", "pressure", "noise", "light", "tof"):
        if metric in user_query.lower():
            targeted_data += (
                f"\n\n=== Targeted InfluxDB — {metric} (last {window}) ===\n"
                + _query_influx_range(metric, window)
            )

    data_bundle = {
        "mode": mode,
        "timestamp_utc": now_utc,
        "requested_time_window": window,
        "sensor_payload_summary": parsed_sensors,
        "influx_recent_history": influx_general
        if influx_general else "(InfluxDB not available or no data in window)",
        "targeted_influx_history": targeted_data.strip() or "N/A",
        "rcms_edge_url": RCMS_EDGE_URL,
        "rcms_snapshot": rcms_snapshot,
        "firebase": "Firebase auth/Firestore available - user is authenticated admin",
        "site_operations": site_operations,
    }

    runtime_context = json.dumps(data_bundle, indent=2, ensure_ascii=False, default=str)

    return {
        "device_data": device_data or "null",
        "user_query": user_query,
        "language": language,
        "context_data": context_data or "",
        "runtime_context": runtime_context,
        "report_datetime": now_utc,
        "datetime": now_utc,
        "bucket": INFLUXDB_BUCKET or "N/A",
        "edge_url": RCMS_EDGE_URL,
        "ts": now_utc,
        "firebase_project": os.getenv("FIREBASE_PROJECT_ID", "N/A"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CrewAI YAML pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _load_yaml_config(name: str) -> dict:
    with (_CONFIG_DIR / name).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _make_llm(provider, timeout: int) -> LLM:
    key = _get_key(provider)
    kwargs: dict = {
        "model": provider.model,
        "api_key": key,
        "temperature": 0.3,
        "timeout": timeout,
        "max_tokens": int(os.getenv("CREWAI_MAX_TOKENS", "4096")),
    }
    if provider.base_url:
        kwargs["base_url"] = provider.base_url
    if provider.extra_headers:
        kwargs["extra_headers"] = provider.extra_headers
    return LLM(**kwargs)


def _available_providers() -> list:
    return [provider for provider in PROVIDERS if _get_key(provider)]


def _agent_tools() -> dict[str, list]:
    influx_tool = InfluxDBQueryTool(
        influx_query_func=influx_query,
        influx_bucket=INFLUXDB_BUCKET,
    )
    return {
        "sensor_agent": [_sensor_parser, influx_tool],
        "edge_device_agent": [
            rcms_full_snapshot_tool,
            rcms_device_list_tool,
            rcms_device_info_tool,
            rcms_device_sensors_tool,
            rcms_system_info_tool,
            rcms_alerts_tool,
        ],
        "context_agent": [],
        "anomaly_agent": [],
        "reasoning_agent": [],
        "report_agent": [],
    }


def _build_agents(llm: LLM) -> dict[str, Agent]:
    agents_cfg = _load_yaml_config("agents.yaml")
    tools_by_agent = _agent_tools()
    agents: dict[str, Agent] = {}
    for key, cfg in agents_cfg.items():
        if not isinstance(cfg, dict):
            continue
        agents[key] = Agent(
            role=_escape_crewai_template(cfg.get("role", key)),
            goal=_escape_crewai_template(cfg.get("goal", "")),
            backstory=_escape_crewai_template(cfg.get("backstory", "")),
            tools=tools_by_agent.get(key, []),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
    return agents


def _task_description(key: str, cfg: dict, mode: str) -> str:
    description = cfg.get("description", "")
    runtime_note = """

Runtime data bundle available to this task:
<runtime_context>
{runtime_context}
</runtime_context>

Use the runtime data bundle as already-retrieved official context. It includes
sensor data, RCMS state, weather/digital-twin alerts, emergency requests,
backend route capabilities, frontend workflows, and available site operations.
You may call your assigned tools only when the task needs fresher or more
specific data.
"""
    if key == "compose_full_report":
        runtime_note += """

Report mode instruction: do not include raw JSON payload dumps. Summarise the
runtime context into clean Markdown tables and prose. Keep only the final
delivery_prompt fenced block.
"""
    elif mode == "chat" and key == "generate_answer":
        runtime_note += """

Chat mode instruction: answer the user's query directly. Return either concise
text with citations or one chart JSON block, matching the task rules.
"""
    return description + runtime_note


_INPUT_PLACEHOLDERS = (
    "device_data",
    "user_query",
    "language",
    "report_datetime",
    "context_data",
    "runtime_context",
    "datetime",
    "bucket",
    "edge_url",
    "ts",
    "firebase_project",
)


def _escape_crewai_template(text: str) -> str:
    """
    CrewAI interpolates task strings with Python-style braces. The YAML contains
    JSON, endpoint, and LaTeX examples. Preserve only the runtime placeholders
    we intentionally pass to kickoff; rewrite every other brace as display text
    so CrewAI cannot treat examples like {id} as missing inputs.
    """
    normalized = _normalize_latex_template_braces(str(text or ""))
    protected: dict[str, str] = {}
    for i, key in enumerate(_INPUT_PLACEHOLDERS):
        token = f"__CREWAI_INPUT_{i}__"
        protected[token] = "{" + key + "}"
        normalized = normalized.replace("{" + key + "}", token)

    normalized = normalized.replace("{", "(").replace("}", ")")

    for token, placeholder in protected.items():
        normalized = normalized.replace(token, placeholder)
    return normalized


def _normalize_latex_template_braces(text: str) -> str:
    """
    CrewAI scans strings for {name} placeholders before execution. LaTeX samples
    such as \\bar{T} and \\frac{1}{n} can be mistaken for missing inputs, even
    after normal format escaping. Keep the examples readable without braces.
    """
    latex_commands = r"(bar|frac|sum|Delta|sqrt|overline|hat|tilde)"
    previous = None
    while previous != text:
        previous = text
        text = _re.sub(
            rf"\\{latex_commands}\{{([^{{}}]+)\}}",
            r"\\\1(\2)",
            text,
        )
        text = _re.sub(
            rf"(\\{latex_commands}(?:\([^()]*\))*)\{{([^{{}}]+)\}}",
            r"\1(\3)",
            text,
        )
    text = _re.sub(r"([_^])\{([^{}]+)\}", r"\1(\2)", text)
    return text


def _build_tasks(agents: dict[str, Agent], mode: str) -> list[Task]:
    tasks_cfg = _load_yaml_config("tasks.yaml")
    if mode == "report":
        task_keys = [
            "fetch_and_validate_sensor_data",
            "fetch_edge_device_data",
            "build_multilingual_context",
            "detect_anomalies",
            "compose_full_report",
        ]
    else:
        task_keys = [
            "fetch_and_validate_sensor_data",
            "fetch_edge_device_data",
            "build_multilingual_context",
            "detect_anomalies",
            "generate_answer",
        ]

    tasks: list[Task] = []
    task_by_key: dict[str, Task] = {}
    for key in task_keys:
        cfg = tasks_cfg.get(key, {})
        agent_key = cfg.get("agent")
        agent = agents.get(agent_key)
        if agent is None:
            raise RuntimeError(f"Task {key} references missing agent {agent_key!r}")

        context: list[Task] = []
        if key == "build_multilingual_context":
            context = [
                task_by_key["fetch_and_validate_sensor_data"],
                task_by_key["fetch_edge_device_data"],
            ]
        elif key == "detect_anomalies":
            context = [
                task_by_key["fetch_and_validate_sensor_data"],
                task_by_key["fetch_edge_device_data"],
                task_by_key["build_multilingual_context"],
            ]
        elif key == "generate_answer":
            context = [
                task_by_key["fetch_and_validate_sensor_data"],
                task_by_key["fetch_edge_device_data"],
                task_by_key["build_multilingual_context"],
                task_by_key["detect_anomalies"],
            ]
        elif key == "compose_full_report":
            context = [
                task_by_key["fetch_and_validate_sensor_data"],
                task_by_key["fetch_edge_device_data"],
                task_by_key["build_multilingual_context"],
                task_by_key["detect_anomalies"],
            ]

        task = Task(
            description=_escape_crewai_template(_task_description(key, cfg, mode)),
            expected_output=_escape_crewai_template(cfg.get("expected_output", "")),
            agent=agent,
            context=context,
        )
        tasks.append(task)
        task_by_key[key] = task
    return tasks


def _coerce_crew_output(result) -> str:
    raw = getattr(result, "raw", None)
    if raw:
        return str(raw).strip()
    return str(result or "").strip()


def _run_yaml_crew(
    device_data: str,
    user_query: str,
    language: str,
    context_data: str,
    mode: str,
    timeout: int,
) -> str:
    inputs = _build_runtime_inputs(
        device_data=device_data,
        user_query=user_query,
        language=language,
        context_data=context_data,
        mode=mode,
    )
    errors: list[str] = []
    providers = _available_providers()
    if not providers:
        raise RuntimeError("No LLM provider key configured for CrewAI execution")

    for provider in providers:
        try:
            print(f"[CrewAI] Trying provider: {provider.name}")
            llm = _make_llm(provider, timeout=timeout)
            agents = _build_agents(llm)
            tasks = _build_tasks(agents, mode=mode)
            crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=False,
            )
            result = crew.kickoff(inputs=inputs)
            text = _coerce_crew_output(result)
            print(f"[CrewAI] OK: {provider.name} responded ({len(text)} chars)")
            return text
        except Exception as exc:
            msg = f"{provider.name}: {type(exc).__name__}: {exc}"
            print(f"[CrewAI] FAIL: {msg}")
            errors.append(msg)

    raise RuntimeError(
        "All CrewAI providers failed:\n" + "\n".join(f"  - {e}" for e in errors)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────────────────────────────────────

def run_crew(
    device_data: str,
    user_query: str,
    language: str = "en",
    context_data: str = "",
) -> str:
    """
    Conversational mode — returns plain text, LaTeX, or a chart JSON block.
    Called by POST /api/crew/chat.
    """
    return _run_yaml_crew(
        device_data=device_data,
        user_query=user_query,
        language=language,
        context_data=context_data,
        mode="chat",
        timeout=55,
    )


def run_crew_report(
    device_data: str,
    user_query: str,
    language: str = "en",
    context_data: str = "",
) -> str:
    """
    Report mode — returns a full Markdown report with delivery prompt.
    Called by POST /api/crew/report.
    """
    result = _run_yaml_crew(
        device_data=device_data,
        user_query=user_query,
        language=language,
        context_data=context_data,
        mode="report",
        timeout=90,
    )
    return _sanitize_report(result)


def _sanitize_report(markdown: str) -> str:
    """Remove common LLM/report artifacts before the UI renders or exports."""
    text = str(markdown or "").strip()

    # Keep the delivery prompt, but remove all raw chart/data JSON code fences.
    delivery_blocks: list[str] = []

    def stash_delivery(match):
        delivery_blocks.append(match.group(0))
        return f"__DELIVERY_PROMPT_{len(delivery_blocks) - 1}__"

    text = _re.sub(r"```delivery_prompt[\s\S]*?```", stash_delivery, text)
    text = _re.sub(r"```json[\s\S]*?```", "", text, flags=_re.I)

    # Remove mojibake that usually comes from emoji status markers in exports.
    replacements = {
        "Ø=ßá": "GREEN",
        "Ø=ß yellow": "YELLOW",
        "Ø=Ý´": "WARNING",
        "Ø=Ô´": "CRITICAL",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Normalize oversized whitespace left behind by stripped blocks.
    text = _re.sub(r"\n{3,}", "\n\n", text).strip()

    for i, block in enumerate(delivery_blocks):
        text = text.replace(f"__DELIVERY_PROMPT_{i}__", block)

    return text
