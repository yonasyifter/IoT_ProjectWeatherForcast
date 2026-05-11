"""
app/routes/rag.py

Dedicated Groq + RAG chat endpoint (independent from Crew route).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import litellm
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.config import GROQ_API_KEY, GROQ_MODEL_ID, INFLUXDB_BUCKET, INFLUXDB_MEASUREMENT
from app.influx import query as influx_query
from app.routes.auth import get_admin_session_user

try:
    from crew.src.tools.voice_tool import transcribe_audio

    VOICE_AVAILABLE = True
except Exception:  # noqa: BLE001
    VOICE_AVAILABLE = False


router = APIRouter()
litellm.telemetry = False
litellm.set_verbose = False


def _safe_json_load(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _latest_devices_context(device_data: str | None, limit: int = 8) -> str:
    parsed = _safe_json_load(device_data)
    if not isinstance(parsed, list):
        return ""

    by_device: dict[str, dict[str, Any]] = {}
    for row in parsed:
        if not isinstance(row, dict):
            continue
        device_id = str(row.get("device_id", "unknown"))
        ts = row.get("time")
        existing = by_device.get(device_id)
        if existing is None:
            by_device[device_id] = row
            continue
        if ts and existing.get("time"):
            if str(ts) > str(existing["time"]):
                by_device[device_id] = row

    selected = list(by_device.values())[:limit]
    if not selected:
        return ""
    return json.dumps(selected, ensure_ascii=True)


def _influx_rag_context(hours: int = 24) -> str:
    if not INFLUXDB_BUCKET or not INFLUXDB_MEASUREMENT:
        return ""
    flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r._measurement == "{INFLUXDB_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity" or r._field == "pressure" or r._field == "noise" or r._field == "light")
  |> aggregateWindow(every: 30m, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_field", "_value"])
'''
    tables = influx_query(flux)
    out: list[dict[str, Any]] = []
    for table in tables:
        for rec in table.records:
            ts = rec.get_time()
            val = rec.get_value()
            fld = rec.get_field()
            if ts is None or val is None or fld is None:
                continue
            try:
                num = round(float(val), 3)
            except (TypeError, ValueError):
                continue
            out.append({"time": ts.isoformat(), "field": fld, "value": num})
            if len(out) >= 400:
                break
        if len(out) >= 400:
            break
    if not out:
        return ""
    return json.dumps(out, ensure_ascii=True)


def _call_groq_rag(query: str, language: str, context_chunks: list[str]) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured")

    model = GROQ_MODEL_ID or "groq/llama-3.3-70b-versatile"
    if not model.startswith("groq/"):
        model = f"groq/{model}"

    system = (
        "You are a Smart Park RAG assistant. "
        "Answer only from provided context chunks. "
        "If context is missing for the question, say explicitly that data is unavailable. "
        "Keep answers concise and operational for park admins. "
        "If user asks for chart/graph data, provide one JSON block only with keys: "
        "chart_type, title, labels, data or datasets, description."
    )
    user = (
        f"Language: {language}\n"
        f"Question: {query}\n\n"
        "Retrieved context chunks:\n"
        + "\n\n".join(f"[chunk {i+1}] {chunk}" for i, chunk in enumerate(context_chunks) if chunk)
    )

    try:
        resp = litellm.completion(
            model=model,
            api_key=GROQ_API_KEY,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=900,
            timeout=45,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Groq RAG inference failed: {exc}") from exc


@router.post(
    "/chat",
    summary="Groq RAG Assistant",
    dependencies=[Depends(get_admin_session_user)],
)
async def rag_chat(
    request: Request,
    user_query: str | None = Form(None),
    device_data: str | None = Form(None),
    audio_file: UploadFile | None = File(None),
    language: str = Form("en"),
) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            user_query = payload.get("user_query", user_query)
            language = payload.get("language", language)
            if "device_data" in payload and not isinstance(payload["device_data"], str):
                device_data = json.dumps(payload["device_data"])
            else:
                device_data = payload.get("device_data", device_data)

    transcript = ""
    if audio_file:
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        if len(audio_bytes) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio file too large (max 25 MB)")
        if not VOICE_AVAILABLE:
            raise HTTPException(status_code=503, detail="Voice transcription is unavailable")
        transcript, err = transcribe_audio(
            audio_bytes=audio_bytes,
            content_type=audio_file.content_type,
            language=language,
        )
        if err and not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe audio")

    query = (transcript or user_query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Please provide text or audio input")

    retrieved = []
    device_chunk = _latest_devices_context(device_data)
    if device_chunk:
        retrieved.append(device_chunk)

    influx_chunk = _influx_rag_context(hours=24)
    if influx_chunk:
        retrieved.append(influx_chunk)

    # deterministic fallback chunk when nothing is available
    if not retrieved:
        retrieved.append(
            json.dumps(
                {
                    "warning": "No sensor context could be retrieved",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                ensure_ascii=True,
            )
        )

    answer = _call_groq_rag(query=query, language=language or "en", context_chunks=retrieved)

    return {
        "transcript": transcript,
        "answer": answer,
        "source": "groq-rag",
        "retrieved_chunks": len(retrieved),
    }

