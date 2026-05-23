"""
app/routes/crew.py

FastAPI router for the CrewAI-powered Smart Park assistant.

Endpoint: POST /api/crew/chat
Auth: Firebase session (Bearer token)
"""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import functools
import json
import os
import re
import smtplib
import ssl
import traceback
from datetime import datetime
from email.message import EmailMessage
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.config import INFLUXDB_BUCKET, INFLUXDB_MEASUREMENT
from app.influx import query as influx_query
from app.routes.auth import get_admin_session_user

try:
    from crew.src.crew import run_crew, run_crew_report

    CREW_AVAILABLE = True
except Exception as crew_err:  # noqa: BLE001
    CREW_AVAILABLE = False
    CREW_IMPORT_ERROR = str(crew_err)

try:
    from crew.src.tools.voice_tool import transcribe_audio

    VOICE_AVAILABLE = True
except Exception:  # noqa: BLE001
    VOICE_AVAILABLE = False

router = APIRouter()


class ReportDeliveryRequest(BaseModel):
    channel: str
    contact: str
    subject: str = "Smart Park Report"
    html: str | None = None
    text: str | None = None

SUPPORTED_LANGUAGES: set[str] = {
    "en",
    "it",
    "fr",
    "de",
    "es",
    "pt",
    "ar",
    "zh",
    "ja",
    "ko",
}

ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "no_input": {
        "en": "Please provide either a text query or an audio recording.",
        "it": "Si prega di fornire una query di testo o una registrazione audio.",
    },
    "audio_empty": {
        "en": "Audio file is empty.",
        "it": "Il file audio e vuoto.",
    },
    "audio_too_large": {
        "en": "Audio file too large (max 25 MB). Please record a shorter message.",
        "it": "File audio troppo grande (max 25 MB). Registra un messaggio piu breve.",
    },
    "transcription_failed": {
        "en": "I could not understand the audio. Please try again or type your question.",
        "it": "Non ho capito l'audio. Riprova o scrivi la tua domanda.",
    },
}


def _err(key: str, language: str) -> str:
    msgs = ERROR_MESSAGES.get(key, {})
    return msgs.get(language, msgs.get("en", "An error occurred."))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _html_to_text(html: str | None) -> str:
    text = re.sub(r"<style[\s\S]*?</style>", "", html or "", flags=re.I)
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|section|h1|h2|h3|li|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _require_report_body(payload: ReportDeliveryRequest) -> tuple[str, str]:
    html = (payload.html or "").strip()
    text = (payload.text or "").strip() or _html_to_text(html)
    if not html and not text:
        raise HTTPException(status_code=400, detail="Report body is empty.")
    return html, text


def _send_report_email(payload: ReportDeliveryRequest) -> None:
    contact = payload.contact.strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", contact):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "465" if _env_bool("SMTP_SSL") else "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    if not smtp_host or not smtp_from:
        raise HTTPException(
            status_code=503,
            detail="Email delivery is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM.",
        )

    html, text = _require_report_body(payload)
    message = EmailMessage()
    message["Subject"] = payload.subject or "Smart Park Report"
    message["From"] = smtp_from
    message["To"] = contact
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    try:
        if _env_bool("SMTP_SSL", smtp_port == 465):
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context(), timeout=30) as smtp:
                if smtp_user and smtp_password:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
                if _env_bool("SMTP_TLS", True):
                    smtp.starttls(context=ssl.create_default_context())
                if smtp_user and smtp_password:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email delivery failed: {exc}") from exc


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"WhatsApp delivery failed: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WhatsApp delivery failed: {exc}") from exc


def _post_form(url: str, payload: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    data = urlparse.urlencode(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"WhatsApp delivery failed: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WhatsApp delivery failed: {exc}") from exc


def _send_report_whatsapp(payload: ReportDeliveryRequest) -> None:
    contact = re.sub(r"[\s()-]", "", payload.contact.strip())
    if not re.match(r"^\+\d{8,15}$", contact):
        raise HTTPException(status_code=400, detail="Please enter a WhatsApp number in international format, for example +393511204817.")

    _, text = _require_report_body(payload)
    message_text = text[:3800]

    meta_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    meta_phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if meta_token and meta_phone_id:
        _post_json(
            f"https://graph.facebook.com/v20.0/{meta_phone_id}/messages",
            {
                "messaging_product": "whatsapp",
                "to": contact.lstrip("+"),
                "type": "text",
                "text": {"preview_url": False, "body": message_text},
            },
            {"Authorization": f"Bearer {meta_token}"},
        )
        return

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_WHATSAPP_FROM")
    if twilio_sid and twilio_token and twilio_from:
        auth = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode("utf-8")).decode("ascii")
        _post_form(
            f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
            {"From": f"whatsapp:{twilio_from}", "To": f"whatsapp:{contact}", "Body": message_text},
            {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        return

    raise HTTPException(
        status_code=503,
        detail=(
            "WhatsApp delivery is not configured. Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID "
            "for Meta Cloud API, or TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM for Twilio."
        ),
    )


def _coerce_json_to_str(value: Any, fallback: str | None) -> str | None:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except Exception:
        return fallback


def _extract_context_payload(context_data: str | None) -> dict[str, Any] | None:
    if not context_data:
        return None
    try:
        parsed = json.loads(context_data)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _extract_chart(answer: str) -> tuple[str, dict[str, Any] | None]:
    """
    Scan the AI answer for a JSON chart block.
    Returns (clean_text, chart_dict_or_none).
    """
    for fence_match in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", answer, re.IGNORECASE):
        raw_json = fence_match.group(1).strip()
        if '"chart_type"' not in raw_json and "'chart_type'" not in raw_json:
            continue
        try:
            chart = json.loads(raw_json)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(chart, dict) or "chart_type" not in chart:
            continue

        clean = (answer[: fence_match.start()] + answer[fence_match.end() :]).strip()
        if not clean and chart.get("description"):
            clean = str(chart["description"])
        return clean, chart

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", answer):
        snippet = answer[match.start() :]
        if '"chart_type"' not in snippet[:500] and "'chart_type'" not in snippet[:500]:
            continue
        try:
            chart, end = decoder.raw_decode(snippet)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(chart, dict) or "chart_type" not in chart:
            continue

        clean = (answer[: match.start()] + snippet[end:]).strip()
        if not clean and chart.get("description"):
            clean = str(chart["description"])
        return clean, chart

    return answer.strip(), None


def _extract_weather(device_data: str | None) -> tuple[str | None, float | None]:
    """Pull the latest real weather prediction fields from raw sensor JSON."""
    if not device_data:
        return None, None
    try:
        data = json.loads(device_data)
        if not isinstance(data, list):
            return None, None

        candidates: list[dict[str, Any]] = []
        for device in data:
            if not isinstance(device, dict):
                continue
            prediction = device.get("weather_prediction")
            if prediction in (None, "", "—", "N/A"):
                continue
            candidates.append(device)

        if not candidates:
            return None, None

        def timestamp_value(item: dict[str, Any]) -> str:
            return str(item.get("time") or item.get("timestamp") or "")

        latest = max(candidates, key=timestamp_value)
        confidence = float(latest.get("prediction_confidence", 0) or 0)
        if 0 < confidence <= 1:
            confidence *= 100
        confidence = max(0, min(100, confidence))
        return str(latest["weather_prediction"]), confidence
    except Exception:
        return None, None
    return None, None


def _is_temperature_query(text: str) -> bool:
    q = text.lower()
    return "temperature" in q or "temp" in q


def _extract_last_days(text: str) -> int | None:
    q = text.lower()
    match = re.search(r"last\s+(\d{1,3})\s+day", q)
    if match:
        return max(1, min(60, int(match.group(1))))
    if "10 days" in q:
        return 10
    return None


def _wants_chart(text: str) -> bool:
    q = text.lower()
    return "chart" in q or "graph" in q or "bar" in q or "plot" in q


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace("%", ""))
    except (TypeError, ValueError):
        return None


def _first_float(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _to_float(row.get(key))
        if value is not None:
            return value
    return None


def _is_edge_resource_query(text: str) -> bool:
    q = text.lower()
    mentions_resource = any(term in q for term in ("cpu", "ram", "memory"))
    mentions_edge = any(term in q for term in ("edge", "eg5120", "device", "gateway"))
    return mentions_resource and mentions_edge


def _latest_device_rows(device_data: str | None) -> list[dict[str, Any]]:
    if not device_data:
        return []
    try:
        rows = json.loads(device_data)
    except Exception:
        return []
    if not isinstance(rows, list):
        return []

    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        device_id = str(row.get("device_id") or row.get("id") or "unknown")
        current = latest.get(device_id)
        row_time = str(row.get("time") or row.get("timestamp") or "")
        current_time = str(current.get("time") or current.get("timestamp") or "") if current else ""
        if current is None or row_time >= current_time:
            latest[device_id] = row

    return sorted(latest.values(), key=lambda item: str(item.get("device_id") or item.get("id") or ""))


def _query_edge_resources_from_snapshot(device_data: str | None) -> dict[str, Any] | None:
    latest_rows = _latest_device_rows(device_data)
    if not latest_rows:
        return None

    lines: list[str] = []
    chart_labels: list[str] = []
    ram_values: list[float | None] = []
    cpu_values: list[float | None] = []

    for row in latest_rows:
        device_id = str(row.get("device_id") or row.get("id") or "unknown")
        cpu_usage = _first_float(row, [
            "EG5120_CPU_Usage",
            "EG5120_CPU_usage",
            "CPU_Usage",
            "CPU_usage",
            "cpu_usage",
            "cpuUsage",
            "cpu_pct",
        ])
        cpu_temp = _first_float(row, [
            "EG5120_CPU_Temprature",
            "EG5120_CPU_Temperature",
            "CPU_temprature",
            "CPU_temperature",
            "cpuTemperature",
        ])
        ram_usage = _first_float(row, [
            "EG5120_RAM_usage",
            "EG5120_RAM_Usage",
            "RAM_Usage",
            "RAM_usage",
            "ram_usage",
            "ramUsage",
        ])
        ram_total = _first_float(row, ["EG5120_RAM_total_mb", "RAM_total_mb", "ram_total_mb"])
        ram_free = _first_float(row, ["EG5120_RAM_free_mb", "RAM_free_mb", "ram_free_mb"])
        if ram_usage is None and ram_total and ram_free is not None:
            ram_usage = ((ram_total - ram_free) / ram_total) * 100

        if cpu_usage is None and cpu_temp is None and ram_usage is None:
            continue

        cpu_text = (
            f"CPU usage {cpu_usage:.1f}%"
            if cpu_usage is not None
            else f"CPU temperature {cpu_temp:.1f} C"
            if cpu_temp is not None
            else "CPU data unavailable"
        )
        ram_text = f"RAM usage {ram_usage:.1f}%" if ram_usage is not None else "RAM data unavailable"
        if ram_total and ram_free is not None:
            ram_text += f" ({ram_total - ram_free:.0f} MB used of {ram_total:.0f} MB)"

        timestamp = row.get("time") or row.get("timestamp") or "unknown time"
        lines.append(f"Device {device_id}: {cpu_text}; {ram_text}; last update {timestamp}.")
        chart_labels.append(f"Device {device_id}")
        cpu_values.append(cpu_usage if cpu_usage is not None else cpu_temp)
        ram_values.append(round(ram_usage, 1) if ram_usage is not None else None)

    if not lines:
        return None

    chart = {
        "chart_type": "bar",
        "title": "Edge Device CPU and RAM",
        "description": "Latest EG5120 resource readings per device. CPU is shown as usage when available, otherwise CPU temperature.",
        "labels": chart_labels,
        "datasets": [
            {
                "label": "CPU usage (%) or CPU temperature (C)",
                "data": cpu_values,
                "backgroundColor": "rgba(239, 68, 68, 0.65)",
                "borderColor": "rgba(220, 38, 38, 1)",
            },
            {
                "label": "RAM usage (%)",
                "data": ram_values,
                "backgroundColor": "rgba(37, 99, 235, 0.65)",
                "borderColor": "rgba(29, 78, 216, 1)",
            },
        ],
    }

    return {
        "answer": "Latest Edge device CPU and RAM readings:\n" + "\n".join(f"- {line}" for line in lines),
        "chart": chart,
    }


def _is_greeting(text: str) -> bool:
    q = re.sub(r"[^a-zA-Z\s]", "", text).lower().strip()
    return q in {"hi", "hello", "helo", "hey", "ciao", "salve"}


def _query_temperature_today() -> dict[str, Any] | None:
    if not INFLUXDB_BUCKET or not INFLUXDB_MEASUREMENT:
        return None
    flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: today())
  |> filter(fn: (r) => r._measurement == "{INFLUXDB_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "temperature")
  |> keep(columns: ["_time", "_value"])
'''
    tables = influx_query(flux)
    points: list[tuple[datetime, float]] = []
    for table in tables:
        for record in table.records:
            ts = record.get_time()
            val = record.get_value()
            if ts is None or val is None:
                continue
            try:
                points.append((ts, float(val)))
            except (TypeError, ValueError):
                continue
    if not points:
        return None

    points.sort(key=lambda x: x[0])
    values = [p[1] for p in points]
    latest_time, latest_value = points[-1]
    avg_value = sum(values) / len(values)
    min_value = min(values)
    max_value = max(values)
    return {
        "answer": (
            f"Today's park temperature: latest {latest_value:.1f} C "
            f"(avg {avg_value:.1f} C, min {min_value:.1f} C, max {max_value:.1f} C). "
            f"Last update: {latest_time.isoformat()}."
        ),
        "chart": None,
    }


def _query_temperature_last_days(days: int) -> dict[str, Any] | None:
    if not INFLUXDB_BUCKET or not INFLUXDB_MEASUREMENT:
        return None
    flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{days}d)
  |> filter(fn: (r) => r._measurement == "{INFLUXDB_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "temperature")
  |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_value"])
'''
    tables = influx_query(flux)
    rows: list[tuple[str, float]] = []
    for table in tables:
        for record in table.records:
            ts = record.get_time()
            val = record.get_value()
            if ts is None or val is None:
                continue
            label = ts.strftime("%Y-%m-%d")
            try:
                rows.append((label, float(val)))
            except (TypeError, ValueError):
                continue
    if not rows:
        return None

    # Deduplicate by date in case multiple series are returned
    by_day: dict[str, float] = {}
    for label, value in rows:
        by_day[label] = value
    labels = sorted(by_day.keys())
    data = [round(by_day[label], 2) for label in labels]

    chart = {
        "chart_type": "bar",
        "title": f"Average Temperature - Last {days} Days",
        "description": "Daily mean temperature from InfluxDB.",
        "labels": labels,
        "datasets": [
            {
                "label": "Temperature (C)",
                "data": data,
                "backgroundColor": "rgba(59, 130, 246, 0.65)",
                "borderColor": "rgba(37, 99, 235, 1)",
            }
        ],
    }
    avg_value = sum(data) / len(data)
    answer = (
        f"Here is the bar chart for the last {days} days. "
        f"Average temperature over this period is {avg_value:.1f} C."
    )
    return {"answer": answer, "chart": chart}


def _query_latest_environment() -> dict[str, Any] | None:
    if not INFLUXDB_BUCKET or not INFLUXDB_MEASUREMENT:
        return None
    flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "{INFLUXDB_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
  |> group(columns: ["device_id", "_field"])
  |> last()
  |> keep(columns: ["_time", "_field", "_value", "device_id"])
'''
    tables = influx_query(flux)
    readings: dict[str, list[tuple[datetime, float, str]]] = {"temperature": [], "humidity": []}

    for table in tables:
        for record in table.records:
            field = record.get_field()
            if field not in readings:
                continue
            ts = record.get_time()
            val = record.get_value()
            if ts is None or val is None:
                continue
            try:
                readings[field].append((ts, float(val), str(record.values.get("device_id", "unknown"))))
            except (TypeError, ValueError):
                continue

    parts: list[str] = []
    latest_times: list[datetime] = []
    device_ids: set[str] = set()

    for field, unit in (("temperature", "C"), ("humidity", "%")):
        values = readings[field]
        if not values:
            continue
        latest_times.extend(ts for ts, _, _ in values)
        device_ids.update(device_id for _, _, device_id in values)
        avg_value = sum(value for _, value, _ in values) / len(values)
        parts.append(f"{field} {avg_value:.1f} {unit}")

    if not parts:
        return None

    latest_time = max(latest_times).isoformat() if latest_times else "unknown"
    device_count = len(device_ids)
    answer = (
        f"Current park readings: {', '.join(parts)}. "
        f"Based on the latest reading from {device_count} device{'s' if device_count != 1 else ''}; "
        f"last update: {latest_time}."
    )
    return {"answer": answer, "chart": None}


@router.post(
    "/chat",
    summary="Smart Park AI Assistant (CrewAI + multi-LLM)",
    dependencies=[Depends(get_admin_session_user)],
)
async def crew_chat(
    request: Request,
    user_query: str | None = Form(None),
    device_data: str | None = Form(None),
    context_data: str | None = Form(None),
    audio_file: UploadFile | None = File(None),
    language: str = Form("en"),
) -> dict[str, Any]:
    if not CREW_AVAILABLE:
        raise HTTPException(status_code=503, detail=f"CrewAI not available: {CREW_IMPORT_ERROR}")

    # Support JSON payloads from web clients for text-only requests.
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            user_query = payload.get("user_query", user_query)
            language = payload.get("language", language)
            device_data = _coerce_json_to_str(payload.get("device_data"), device_data)
            context_data = _coerce_json_to_str(payload.get("context_data"), context_data)

    lang = (language or "en").lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"

    context_payload = _extract_context_payload(context_data)

    if not user_query and not audio_file:
        raise HTTPException(status_code=400, detail=_err("no_input", lang))

    transcript = ""
    if audio_file:
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail=_err("audio_empty", lang))
        if len(audio_bytes) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=_err("audio_too_large", lang))

        if VOICE_AVAILABLE:
            transcript, transcription_error = transcribe_audio(
                audio_bytes=audio_bytes,
                content_type=audio_file.content_type,
                language=lang,
            )
            if transcription_error and not transcript:
                return {
                    "transcript": transcript,
                    "answer": _err("transcription_failed", lang),
                    "chart": None,
                    "weather_prediction": None,
                    "prediction_confidence": None,
                    "language": lang,
                    "context": context_payload,
                }

    effective_query = transcript or user_query
    if not effective_query:
        return {
            "transcript": transcript,
            "answer": _err("transcription_failed", lang),
            "chart": None,
            "weather_prediction": None,
            "prediction_confidence": None,
            "language": lang,
            "context": context_payload,
        }

    weather_prediction, prediction_confidence = _extract_weather(device_data)
    timeout_seconds = int(os.getenv("CREW_TIMEOUT_SECONDS", "45"))

    if _is_edge_resource_query(effective_query):
        direct = _query_edge_resources_from_snapshot(device_data)
        if direct:
            return {
                "transcript": transcript,
                "answer": direct["answer"],
                "chart": direct.get("chart"),
                "weather_prediction": weather_prediction,
                "prediction_confidence": prediction_confidence,
                "language": lang,
                "context": context_payload,
            }
        return {
            "transcript": transcript,
            "answer": (
                "I could not find Edge device CPU/RAM fields in the latest sensor snapshot. "
                "Expected fields include EG5120_CPU_Temprature, EG5120_RAM_total_mb, and EG5120_RAM_free_mb."
            ),
            "chart": None,
            "weather_prediction": weather_prediction,
            "prediction_confidence": prediction_confidence,
            "language": lang,
            "context": context_payload,
        }

    # Deterministic temperature analytics directly from InfluxDB.
    if _is_temperature_query(effective_query):
        days = _extract_last_days(effective_query)
        wants_chart = _wants_chart(effective_query)
        direct_error: str | None = None
        try:
            if days is not None and (wants_chart or days >= 2):
                direct = _query_temperature_last_days(days)
            elif "today" in effective_query.lower():
                direct = _query_temperature_today()
            else:
                direct = _query_latest_environment()
        except Exception as exc:
            direct_error = str(exc)
            direct = None
        if direct:
            return {
                "transcript": transcript,
                "answer": direct["answer"],
                "chart": direct.get("chart"),
                "weather_prediction": weather_prediction,
                "prediction_confidence": prediction_confidence,
                "language": lang,
                "context": context_payload,
            }
        return {
            "transcript": transcript,
            "answer": (
                "I could not read temperature data from InfluxDB right now. "
                "Please verify INFLUXDB_BUCKET / INFLUXDB_MEASUREMENT and try again."
            ),
            "chart": None,
            "weather_prediction": weather_prediction,
            "prediction_confidence": prediction_confidence,
            "language": lang,
            "context": {
                **(context_payload or {}),
                "debug": {"temperature_query_error": direct_error} if direct_error else None,
            },
        }

    if _is_greeting(effective_query):
        return {
            "transcript": transcript,
            "answer": "Hello. How can I help you understand the park conditions today?",
            "chart": None,
            "weather_prediction": weather_prediction,
            "prediction_confidence": prediction_confidence,
            "language": lang,
            "context": context_payload,
        }

    pool: concurrent.futures.ThreadPoolExecutor | None = None
    try:
        loop = asyncio.get_event_loop()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        raw_answer = await asyncio.wait_for(
            loop.run_in_executor(
                pool,
                functools.partial(
                    run_crew,
                    device_data=device_data or "",
                    user_query=effective_query,
                    language=lang,
                    context_data=json.dumps(context_payload) if context_payload else "",
                ),
            ),
            timeout=timeout_seconds,
        )
        raw_answer = str(raw_answer or "")
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"AI assistant timed out after {timeout_seconds}s. Please retry with a shorter prompt.",
        )
    except Exception as exc:
        traceback.print_exc()
        return {
            "transcript": transcript,
            "answer": (
                "The AI provider is temporarily unavailable, so I cannot generate "
                "a full assistant response right now. Please retry in a moment."
            ),
            "chart": None,
            "weather_prediction": weather_prediction,
            "prediction_confidence": prediction_confidence,
            "language": lang,
            "context": {
                **(context_payload or {}),
                "debug": {"crew_pipeline_error": str(exc)},
            },
        }
    finally:
        if pool:
            pool.shutdown(wait=False, cancel_futures=True)

    answer_text, chart_data = _extract_chart(raw_answer)
    return {
        "transcript": transcript,
        "answer": answer_text,
        "chart": chart_data,
        "weather_prediction": weather_prediction,
        "prediction_confidence": prediction_confidence,
        "language": lang,
        "context": context_payload,
    }


@router.post(
    "/report",
    summary="Generate a full Smart Park analysis report (Markdown)",
    dependencies=[Depends(get_admin_session_user)],
)
async def crew_report(
    request: Request,
    user_query: str | None = Form(None),
    device_data: str | None = Form(None),
    context_data: str | None = Form(None),
    language: str = Form("en"),
) -> dict[str, Any]:
    """
    Generate a comprehensive Markdown analysis report using the full
    multi-agent crew (sensor data + RCMS Edge OpenAPI + anomaly detection).
    Returns {"report": "<markdown string>", "language": "en"}.
    """
    if not CREW_AVAILABLE:
        raise HTTPException(status_code=503, detail=f"CrewAI not available: {CREW_IMPORT_ERROR}")

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            user_query = payload.get("user_query", user_query)
            language = payload.get("language", language)
            device_data = _coerce_json_to_str(payload.get("device_data"), device_data)
            context_data = _coerce_json_to_str(payload.get("context_data"), context_data)

    lang = (language or "en").lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"

    effective_query = user_query or "Generate a full Smart Park analysis report."
    context_payload = _extract_context_payload(context_data)

    # Fetch fresh device snapshot for the report
    if not device_data:
        try:
            from app.influx import query as influx_query
            from app.config import INFLUXDB_BUCKET, INFLUXDB_MEASUREMENT as meas
            flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "{meas}")
  |> last()
  |> keep(columns: ["_time","_field","_value","device_id"])
'''
            tables = influx_query(flux)
            by_device: dict[str, dict] = {}
            for table in tables:
                for rec in table.records:
                    dev = str(rec.values.get("device_id", "unknown"))
                    if dev not in by_device:
                        by_device[dev] = {"device_id": dev}
                    by_device[dev][rec.get_field()] = rec.get_value()
            if by_device:
                device_data = json.dumps(list(by_device.values()))
        except Exception:
            pass

    timeout_seconds = int(os.getenv("CREW_TIMEOUT_SECONDS", "120"))

    pool: concurrent.futures.ThreadPoolExecutor | None = None
    try:
        loop = asyncio.get_event_loop()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        markdown_report = await asyncio.wait_for(
            loop.run_in_executor(
                pool,
                functools.partial(
                    run_crew_report,
                    device_data=device_data or "",
                    user_query=effective_query,
                    language=lang,
                    context_data=json.dumps(context_payload) if context_payload else "",
                ),
            ),
            timeout=timeout_seconds,
        )
        markdown_report = str(markdown_report or "")
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Report generation timed out after {timeout_seconds}s.",
        )
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")
    finally:
        if pool:
            pool.shutdown(wait=False, cancel_futures=True)

    return {
        "report": markdown_report,
        "language": lang,
        "query": effective_query,
    }
