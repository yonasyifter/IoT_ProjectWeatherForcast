# Smart Park Backend — v2.0 (CrewAI Edition)

## Overview

FastAPI backend for the Smart Park IoT platform.  
This version replaces the single-LLM RAG approach with a **CrewAI multi-agent pipeline** that is multilingual and speech-aware out of the box.

---

## Architecture

```
app/
├── main.py                     # FastAPI app, routers, CORS, lifespan
├── config.py                   # Env var loading
├── auth.py                     # Firebase auth helpers
├── database.py                 # Firebase init
├── influx.py                   # InfluxDB client
├── models.py / schemas.py
└── routes/
    ├── auth.py                 # Auth endpoints
    ├── weather.py              # Weather data endpoints
    └── crew.py                 ★ NEW — CrewAI chat endpoint

crew/
└── src/
    ├── crew.py                 ★ CrewAI pipeline (agents + tasks)
    ├── config/
    │   ├── agents.yaml         ★ Agent roles, goals, backstories
    │   └── tasks.yaml          ★ Task descriptions + expected outputs
    └── tools/
        ├── sensor_tool.py      ★ IoT data parser (BaseTool)
        └── voice_tool.py       ★ Groq Whisper STT
```

---

## CrewAI Pipeline

The assistant uses a **3-agent sequential pipeline** per request:

| Step | Agent | Role |
|------|-------|------|
| 1 | **SensorAgent** | Validates and parses the IoT JSON payload using `SensorDataTool` |
| 2 | **ContextAgent** | Formats sensor data into multilingual, human-readable context |
| 3 | **ReasoningAgent** | Answers the user query, grounded in the context, in the correct language |

All agents use `groq/llama-3.3-70b-versatile` via the CrewAI LLM abstraction.

---

## API Endpoint

### `POST /api/crew/chat`
**Auth:** Firebase Bearer token required.

**Form fields (multipart/form-data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_query` | string | ✗* | Visitor's text question |
| `device_data` | string | ✗ | JSON array of IoT readings |
| `audio_file` | file | ✗* | Audio for STT (WAV, MP3, OGG, WebM…) |
| `language` | string | ✗ | ISO-639-1 code (default: `en`) |

*At least one of `user_query` or `audio_file` is required.

**Response:**
```json
{
  "transcript": "transcribed audio text, or empty string",
  "answer": "AI response in the requested language",
  "weather_prediction": "Sunny",
  "prediction_confidence": 82.5,
  "language": "it"
}
```

---

## Supported Languages

`en` · `it` · `fr` · `de` · `es` · `pt` · `ar` · `zh` · `ja` · `ko`

Error messages are localised for `en`, `it`, `fr`, `de`, `es`.  
Agent reasoning and final answers respect the `language` field for all supported codes.

---

## Environment Variables

```env
# Groq (LLM + Whisper STT)
GROQ_API_KEY=gsk_...

# InfluxDB
INFLUXDB_URL=http://...
INFLUXDB_TOKEN=...
INFLUXDB_ORG=...
INFLUXDB_BUCKET=...
INFLUXDB_MEASUREMENT=...

# Firebase
FIREBASE_PROJECT_ID=...
FIREBASE_PRIVATE_KEY_ID=...
FIREBASE_PRIVATE_KEY=...
FIREBASE_CLIENT_EMAIL=...
FIREBASE_CLIENT_ID=...
FIREBASE_CERT_URL=...
FIREBASE_CREDENTIALS_PATH=...

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:5173,...
```

---

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/

---

## Migration from v1 (RAG → CrewAI)

| v1 | v2 |
|----|-----|
| `POST /api/rag/chat` | `POST /api/crew/chat` (same form fields) |
| `app/routes/rag.py` (monolithic) | `app/routes/crew.py` + `crew/src/` |
| Single Groq LLM call | 3-agent CrewAI sequential pipeline |
| `langchain-groq` dependency | `crewai` + `crewai[tools]` |
| Hardcoded EN/IT prompts | YAML-driven, any ISO-639-1 language |
| Voice: inline in route | `crew/src/tools/voice_tool.py` |
