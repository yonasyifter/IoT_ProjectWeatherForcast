# Smart Park IoT + AI Dashboard

Environmental monitoring and device-management platform for a smart park deployment at
I Giganti della Sila / Riserva Naturale Biogenetica di Fallistro.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-3-4FC08D?style=flat&logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=flat&logo=vite&logoColor=white)
![InfluxDB](https://img.shields.io/badge/InfluxDB-22ADF6?style=flat&logo=influxdb&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=flat&logo=firebase&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

## Overview

This repository contains a FastAPI backend and a Vue 3 admin dashboard for monitoring smart-park sensor data, Robustel RCMS devices, weather conditions, and AI-generated operational reports.

The system is built around:

- Environmental telemetry stored in InfluxDB.
- Firebase-backed authentication and project data.
- A Vue admin dashboard for sensor maps, charts, RCMS devices, alerts, GPS tracking, and AI-agent tools.
- A FastAPI backend exposing weather, auth, RAG, Crew/AI, and RCMS proxy endpoints.
- Robustel EG5120 / S6000U field hardware integration.
- Optional report delivery through SMTP email and WhatsApp providers.

## Current Repository Structure

```text
ProjectX_web/
├── admin-side/                  # Vue 3 + Vite admin dashboard
│   ├── src/
│   │   ├── pages/               # Sensor, weather, AI, RCMS, docs/help pages
│   │   ├── components/          # Shared Vue components
│   │   ├── services/            # API clients, including RCMS proxy client
│   │   └── utils/               # Auth, Firebase, API helpers
│   ├── package.json
│   └── vite.config.js
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── routes/              # auth, weather, crew, rag, rcms routes
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # Firebase initialization
│   │   └── influx.py            # InfluxDB helpers
│   ├── crew/                    # AI/Crew support code
│   ├── requirements.txt
│   └── .env                     # Local backend configuration, not for git
├── backend.Dockerfile
├── frontend.Dockerfile
├── compose.yaml
├── nginx.conf
└── README.md
```

## Features

- Live sensor dashboard with device cards, maps, current readings, and health gauges.
- Historical chart pages for temperature, humidity, pressure, sound, prediction-time distribution, and other telemetry.
- RCMS dashboard, device management, GPS tracking, alerts, and remote action pages.
- AI-agent page with conversational Q&A, statistical analysis, visualization, device health, anomaly detection, and full-report generation.
- Report export to PDF/DOC-style documents, with optional delivery by email or WhatsApp.
- Firebase authentication for admin access.
- InfluxDB-backed environmental data queries.

## Technology Stack

| Area | Technology |
| --- | --- |
| Frontend | Vue 3, Vite, Bootstrap, Bootstrap Icons, Leaflet, Chart.js, ECharts |
| Backend | FastAPI, Uvicorn, Pydantic, ORJSON |
| Data | InfluxDB Cloud/local InfluxDB, Firebase Admin SDK |
| AI | Groq, LiteLLM, OpenRouter, CrewAI support code |
| Device management | Robustel RCMS OpenAPI via backend HMAC proxy |
| Export/delivery | jsPDF/html2canvas frontend export, SMTP, WhatsApp provider integrations |
| Deployment | Docker, Docker Compose, Nginx |

## Prerequisites

For local development:

- Python 3.11+
- Node.js 20.19+ or 22.12+
- npm
- Docker and Docker Compose, if running the containerized stack

## Local Development

### 1. Clone and enter the project

```bash
git clone <repository-url>
cd ProjectX_web
```

### 2. Configure the backend

Create or update `backend/.env`.

Minimum commonly used variables:

```env
# InfluxDB
INFLUXDB_URL=https://your-influxdb-url
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=your-org
INFLUXDB_BUCKET=your-bucket
INFLUXDB_MEASUREMENT=your-measurement

# Firebase Admin
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-...@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/service-account.json

# LLM providers. Set at least one.
GROQ_API_KEY=your-groq-key
GROQ_MODEL_ID=groq/llama-3.3-70b-versatile
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL_ID=openrouter/meta-llama/llama-3.3-70b-instruct

# RCMS proxy
RCMS_BASE=https://rcms-cloud.robustel.net
RCMS_CLIENT_ID=your-rcms-client-id
RCMS_CLIENT_SECRET=your-rcms-client-secret

# Report delivery, optional
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-user
SMTP_PASSWORD=your-password
SMTP_FROM=reports@example.com
SMTP_TLS=true
SMTP_SSL=false
WHATSAPP_ACCESS_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id

# CORS for local frontend
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Do not commit `.env`, Firebase service-account JSON files, API keys, SMTP credentials, or RCMS secrets.

### 3. Run the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API docs / Swagger UI: `http://localhost:8000/`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

### 4. Run the frontend

In another terminal:

```bash
cd admin-side
npm install
npm run dev
```

Frontend URL:

- Vite dev server: `http://localhost:5173`

The frontend calls `/api/...` endpoints. In development, ensure the Vite proxy or `VITE_BACKEND_URL` points to the FastAPI backend if your local setup does not already proxy requests.

## Docker Compose

Build and run the production-style stack:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Stop services:

```bash
docker compose down
```

Current `compose.yaml` exposes:

| Service | URL |
| --- | --- |
| Admin dashboard, Nginx production build | `http://localhost` |
| FastAPI backend | `http://localhost:8000` |
| API docs / Swagger UI | `http://localhost:8000/` |
| ReDoc | `http://localhost:8000/redoc` |
| Health check | `http://localhost:8000/health` |

Note: the Compose file currently passes only a small environment set to the backend container. For a real deployment, provide the backend variables through an `env_file`, container secrets, or the cloud runtime environment.

## Main API Routes

The backend registers these route groups:

| Route group | Purpose |
| --- | --- |
| Auth routes | Admin/session authentication |
| `/api/weather` | Weather, forecast, and sensor telemetry queries |
| `/api/crew` | AI-agent requests, reports, report delivery |
| `/api/rcms` | Robustel RCMS OpenAPI proxy |
| `/api/rag` | RAG assistant endpoints |
| `/health` | Backend health check |

Example:

```bash
curl "http://localhost:8000/api/weather/forecast/?minutes=60&measurement=Sensor_S6000U_data_GSP2"
```

## RCMS Notes

RCMS calls are signed server-side by `backend/app/routes/rcms.py`. The frontend must not hold the RCMS HMAC secret.

Important details discovered during integration:

- Device registration uses `/api/gm/devices`.
- RCMS device area must be sent as a code such as `EUR`, `EA`, `EA2`, `NA`, `SA`, or `AU`.
- Device list status may arrive as `onlineStatus`; older UI code may refer to `deviceOnLineStatus`.
- GPS history may arrive as `latitude`, `longitude`, and `timestamp`, so the frontend normalizes these fields before rendering.
- Alert endpoints can validly return an empty `data: []` even when the endpoint is working.

## Frontend Pages

The admin dashboard includes:

- Sensor dashboard
- Weather page
- Side navigation pages for grid/map/chart views
- AI Agent page
- RCMS dashboard
- RCMS alerts
- RCMS GPS tracking
- RCMS device management
- Documentation and help pages

## Build and Verification

Frontend production build:

```bash
cd admin-side
npm run build
```

Backend syntax check:

```bash
python3 -m py_compile backend/app/main.py backend/app/routes/*.py
```

Health check after starting the backend:

```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Frontend cannot reach the backend

Check the backend:

```bash
curl http://localhost:8000/health
```

If using local Vite development, make sure `ALLOWED_ORIGINS` includes `http://localhost:5173` and that the frontend is using the correct backend URL or proxy.

### InfluxDB errors

Verify these variables in `backend/.env`:

- `INFLUXDB_URL`
- `INFLUXDB_TOKEN`
- `INFLUXDB_ORG`
- `INFLUXDB_BUCKET`
- `INFLUXDB_MEASUREMENT`

Also confirm that the configured measurement matches the data written by the gateway.

### Firebase private key errors

Firebase private keys often need escaped newlines when stored in `.env`:

```env
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

Alternatively set `FIREBASE_CREDENTIALS_PATH` to an absolute path for a service-account JSON file.

### RCMS device registration fails

Confirm:

- `RCMS_CLIENT_ID` and `RCMS_CLIENT_SECRET` are configured in the backend environment.
- The SN and IMEI/MAC belong to the same Robustel device.
- The selected model exactly matches RCMS's model list.
- The area sent to RCMS is a code, for example `EUR`, not the label `Europe`.
- The device is not already bound to another RCMS account.

### Report delivery is not working

For email delivery, configure:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`

For WhatsApp delivery, configure the provider credentials required by the backend delivery route.

### Docker port conflicts

Edit `compose.yaml` and change the host-side port mapping. For example:

```yaml
ports:
  - "8080:80"
```

Then restart:

```bash
docker compose down
docker compose up --build
```

## Security Notes

- Never commit `.env` files, Firebase credentials, API keys, RCMS credentials, or SMTP passwords.
- Keep RCMS signing on the backend only.
- Restrict `ALLOWED_ORIGINS` in production.
- Rotate any credential that was accidentally committed or shared.
- Review CORS, authentication, and report-delivery settings before production use.

## About the Reserve

I Giganti della Sila / Riserva Naturale Biogenetica di Fallistro is a protected forest in Sila National Park near Camigliatello Silano, Province of Cosenza, Calabria, Italy.

The reserve is known for ancient Laricio pine trees, some more than 350 years old and up to about 45 metres tall. It is managed by FAI - Fondo Ambiente Italiano.

More information: https://fondoambiente.it/i-giganti-della-sila-eng/

## License and Academic Context

This project was developed for educational and research purposes as part of an IoT smart-park system. It should be reviewed, secured, and tested further before production deployment.
