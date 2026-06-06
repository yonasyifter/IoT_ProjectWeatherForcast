![alt text](image.png) ![alt text](image-1.png)
![alt text](image-2.png) ![alt text](image-3.png)
<div align="center">

# 🌲 Smart Park IoT + AI Weather Forecast System

### Real-time Environmental Monitoring & Intelligent Park Management for *I Giganti della Sila*

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-Admin%20Dashboard-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-Frontend-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-Auth%20%26%20Data-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![InfluxDB](https://img.shields.io/badge/InfluxDB-Time%20Series-22ADF6?style=for-the-badge&logo=influxdb&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-Web%20Server-009639?style=for-the-badge&logo=nginx&logoColor=white)

**Smart Park IoT** is a full-stack IoT and AI platform designed to collect, monitor, visualize, and analyze environmental data from a protected natural reserve. It combines IoT sensing, cloud services, an AI assistant, and an interactive admin dashboard into one deployable system.

[🚀 Quick Start](#-quick-start) • [🏗 Architecture](#-system-architecture) • [📁 Structure](#-repository-structure) • [🔌 API](#-api-overview) • [🛡 Security Notes](#-security-notes)

</div>

---

## 📌 Project Overview

This repository contains an IoT-based weather forecasting and environmental monitoring system for **I Giganti della Sila – Riserva Naturale Biogenetica di Fallistro**, located in **Sila National Park, Calabria, Italy**.

The system is designed to support:

- 🌡️ **Environmental monitoring** using live sensor data
- 📊 **Administrative visualization** through a Vue.js dashboard
- ☁️ **Cloud-connected IoT data management** using FastAPI, InfluxDB, Firebase, and RCMS integrations
- 🤖 **AI-powered assistance** through LLM/RAG endpoints
- 🧭 **Smart park decision support** for staff and visitors

> **Project Type:** University IoT course project / prototype  
> **Status:** Educational and demonstration-ready  
> **Main Goal:** Connect field IoT infrastructure with cloud dashboards and intelligent backend services

---

## ✨ Key Features

| Category | Features |
|---|---|
| 📡 IoT Monitoring | Collect and process weather/environmental sensor data from IoT devices |
| 🌦 Weather Forecasting | Backend endpoint for querying time-windowed weather measurements |
| 📊 Admin Dashboard | Vue.js dashboard for sensors, weather map, visitor density, charts, RCMS pages, and AI agent tools |
| 🔐 Authentication | Firebase-powered admin authentication flow |
| 🤖 AI Assistant | RAG and AI assistant routes using LLM provider configuration |
| ☁️ Cloud & Storage | InfluxDB time-series storage, Firebase integration, RCMS device-management support |
| 🐳 Deployment | Dockerized FastAPI backend and Nginx-served Vue frontend |
| 🩺 Health Checks | `/health` endpoint for service monitoring |

---

## 🏗 System Architecture

```mermaid
flowchart TB
    subgraph Edge["🌲 Edge / Field Layer"]
        Sensor["Environmental Sensors"]
        Gateway["Robustel EG5120 Gateway"]
        NodeRED["Node-RED / Edge Logic"]
        Sensor --> Gateway --> NodeRED
    end

    subgraph Cloud["☁️ Cloud & Backend Layer"]
        API["FastAPI Backend"]
        Influx[("InfluxDB Time-Series DB")]
        Firebase[("Firebase Auth / Firestore")]
        RCMS["Robustel RCMS"]
        LLM["Groq / OpenRouter AI Providers"]
    end

    subgraph Apps["🖥 Application Layer"]
        Admin["Vue.js Admin Dashboard"]
        Docs["Swagger / ReDoc API Docs"]
        Chat["AI / RAG Assistant"]
    end

    NodeRED --> API
    API --> Influx
    API --> Firebase
    API --> RCMS
    API --> LLM
    Admin --> API
    Docs --> API
    Chat --> API
```

### Main Flow

1. **Sensors and gateway** collect environmental data from the park.
2. **FastAPI backend** receives and exposes weather, auth, AI, RCMS, and RAG services.
3. **InfluxDB** stores time-series sensor measurements.
4. **Firebase** supports authentication and cloud data integration.
5. **Vue.js dashboard** gives administrators a clean interface to monitor and interact with the system.
6. **AI/RAG endpoints** provide assistant capabilities for smarter interaction with project data and services.

---

## 🧰 Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend API | **FastAPI**, **Uvicorn**, **ORJSON** | REST API, health checks, weather queries, AI routes |
| Backend Runtime | **Python 3.11** | Main API runtime |
| Time-Series DB | **InfluxDB Client** | Query and manage sensor telemetry |
| Authentication / Cloud | **Firebase Admin**, Firebase frontend SDK | Admin login and cloud data services |
| AI / RAG | **Groq**, **LiteLLM**, **OpenRouter**, **CrewAI** | AI assistant and LLM provider routing |
| Frontend | **Vue.js 3**, **Vite**, **Pinia** | Admin dashboard SPA |
| UI & Maps | **Bootstrap 5**, **Bootstrap Icons**, **Leaflet**, **Chart.js**, **ECharts** | Responsive UI, maps, and visualizations |
| Server | **Nginx** | Serves production frontend build |
| Deployment | **Docker**, **Docker Compose** | Containerized local and cloud deployment |
| Cloud Target | **AWS ECR-ready images** | Image names configured for cloud deployment |

---

## 📁 Repository Structure

```text
IoT_ProjectWeatherForcast/
│
├── admin-side/                  # Vue.js admin dashboard
│   ├── src/
│   │   ├── components/          # Dashboard, chatbot, layout, visitor and chart components
│   │   ├── pages/               # Sensor, weather, RCMS, docs, help, AI agent pages
│   │   ├── views/               # Login/auth views
│   │   └── auth/                # Admin authentication store and logic
│   ├── package.json             # Frontend dependencies and scripts
│   └── vite.config.*            # Vite configuration
│
├── backend/                     # FastAPI backend application
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Environment-based configuration
│   │   ├── routes/              # Auth, weather, crew, RCMS, and RAG API routes
│   │   ├── database.py          # Firebase / database initialization logic
│   │   ├── influx.py            # InfluxDB query helpers
│   │   └── schemas.py           # API response/request schemas
│   ├── crew/                    # AI / CrewAI related logic and configuration
│   └── requirements.txt         # Python dependencies
│
├── backend.Dockerfile           # FastAPI production image
├── frontend.Dockerfile          # Vue build + Nginx production image
├── compose.yaml                 # Docker Compose service orchestration
├── nginx.conf                   # Frontend Nginx SPA routing config
└── README.md                    # Project documentation
```

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yonasyifter/IoT_ProjectWeatherForcast.git
cd IoT_ProjectWeatherForcast
```

### 2. Configure Environment Variables

Create a `.env` file for local backend development or provide the variables through Docker Compose/cloud secrets.

```bash
cp .env.example .env 2>/dev/null || touch .env
```

Add the required values:

```env
# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=your_bucket
INFLUXDB_MEASUREMENT=your_measurement

# Firebase
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your_service_account_email
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CERT_URL=your_cert_url
FIREBASE_CREDENTIALS_PATH=path/to/firebase-service-account.json

# AI Providers - set at least one
GROQ_API_KEY=your_groq_key
GROQ_MODEL_ID=groq/llama-3.3-70b-versatile
CREWAI_GROQ_MAX_TOKENS=4096
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL_ID=openrouter/meta-llama/llama-3.3-70b-instruct
CREWAI_OPENROUTER_MAX_TOKENS=384

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost
```

> For Docker deployments, add these variables under the `fastapi.environment` section in `compose.yaml`, use an `env_file`, or configure them as cloud/runtime secrets.

### 3. Build and Run with Docker Compose

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up --build -d
```

### 4. Open the Services

| Service | URL |
|---|---|
| Admin Dashboard | http://localhost |
| FastAPI Backend | http://localhost:8000 |
| API Docs / Swagger UI | http://localhost:8000/ |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

### 5. Stop the System

```bash
docker compose down
```

---

## 💻 Local Development

### Backend Development

```bash
cd backend
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:

```text
http://localhost:8000
```

### Frontend Development

```bash
cd admin-side
npm install
npm run dev
```

Frontend dev server will usually run at:

```text
http://localhost:5173
```

### Production Frontend Build

```bash
cd admin-side
npm run build
npm run preview
```

---

## 🔌 API Overview

The backend registers the following main route groups:

| Route Group | Description |
|---|---|
| `/health` | Service health endpoint |
| `/api/weather` | Weather and sensor data endpoints |
| `/api/crew` | AI assistant / CrewAI endpoints |
| `/api/rcms` | Robustel RCMS integration endpoints |
| `/api/rag` | Retrieval-Augmented Generation assistant endpoints |
| Auth routes | Authentication-related backend routes |

### Weather Forecast Endpoint

```http
GET /api/weather/forecast/?minutes=60&measurement=<measurement_name>
```

Example:

```bash
curl "http://localhost:8000/api/weather/forecast/?minutes=60&measurement=weather"
```

Response shape:

```json
[
  {
    "time": "2026-01-01T12:00:00+00:00",
    "device_id": "sensor-001",
    "temperature": 22.4,
    "humidity": 61.2
  }
]
```

> Exact fields depend on what the sensor/gateway writes into InfluxDB.

---

## 🖥 Admin Dashboard Modules

The Vue dashboard includes multiple operational pages:

- 📊 **Sensor Dashboard** — live and historical environmental monitoring
- 🌦 **Weather Map** — weather-focused interface and map support
- 👥 **Visitor Density** — visitor-related monitoring section
- 🛰 **RCMS Dashboard** — device overview and remote management links
- 🚨 **RCMS Alerts** — alerts and alarms interface
- 📍 **RCMS GPS** — GPS tracking page
- 🧩 **RCMS Devices** — device management page
- 🤖 **AI Agent** — AI-powered assistant interface
- 💬 **Chatbot Assistant** — embedded assistant component
- 🔐 **Admin Login** — Firebase-based authentication flow

---

## 🐳 Docker Services

The current Compose configuration defines:

| Service | Container Role | Port |
|---|---|---|
| `fastapi` | Python FastAPI backend | `8000:8000` |
| `admin-side` | Vue production build served by Nginx | `80:80` |

Useful commands:

```bash
# Start everything
docker compose up --build

# Start in background
docker compose up -d --build

# View logs
docker compose logs -f

# View backend logs only
docker compose logs -f fastapi

# Rebuild cleanly
docker compose down
docker compose build --no-cache
docker compose up
```

---

## 🛡 Security Notes

Before using this repository publicly or deploying it anywhere, review these items carefully:

- 🔑 **Never commit real API keys** to the repository.
- 🔁 **Rotate any key that was previously committed**, even if it was committed by accident.
- 🔐 Use `.env`, Docker secrets, GitHub Actions secrets, AWS secrets, or another secure secret manager.
- 🚫 Add `.env`, Firebase service-account JSON files, and local credentials to `.gitignore`.
- 🌍 Restrict `ALLOWED_ORIGINS` in production instead of allowing broad CORS access.
- 🧪 Treat this as an educational prototype until authentication, authorization, validation, rate limiting, and deployment hardening are reviewed.

Recommended `.gitignore` additions:

```gitignore
.env
*.env
firebase-service-account*.json
serviceAccountKey.json
__pycache__/
.venv/
node_modules/
dist/
.DS_Store
```

---

## 🧪 Testing & Verification

After starting the system, verify the backend:

```bash
curl http://localhost:8000/health
```

Expected result:

```json
{
  "status": "ok",
  "version": "3.0.0",
  "llm_providers": []
}
```

Check API documentation:

```text
http://localhost:8000/
http://localhost:8000/redoc
```

Check running containers:

```bash
docker compose ps
```

---

## 🛠 Troubleshooting

### Backend container exits immediately

Check logs:

```bash
docker compose logs fastapi
```

Common causes:

- Missing InfluxDB variables
- Missing Firebase variables
- Invalid private key formatting
- Missing AI provider key

### Frontend cannot reach backend

Make sure the backend is running:

```bash
curl http://localhost:8000/health
```

For local frontend development, set the frontend API base URL to the backend address, for example:

```env
VITE_BACKEND_URL=http://localhost:8000
```

### CORS errors in browser

Update:

```env
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost
```

Then restart the backend.

### Firebase private key errors

Firebase private keys often require escaped new lines:

```env
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_KEY\n-----END PRIVATE KEY-----\n"
```

### Port 80 is already in use

Change the frontend port in `compose.yaml`:

```yaml
ports:
  - "8080:80"
```

Then open:

```text
http://localhost:8080
```

---

## 🧭 Roadmap

Potential next improvements:

- [ ] Add `.env.example` with safe placeholder values
- [ ] Add screenshots or GIF demo of the admin dashboard
- [ ] Add automated backend tests with `pytest`
- [ ] Add frontend tests and linting
- [ ] Add GitHub Actions CI workflow
- [ ] Add API examples for RCMS, RAG, auth, and AI assistant endpoints
- [ ] Add deployment guide for AWS / cloud hosting
- [ ] Add production security checklist

---

## 🤝 Contributing

Contributions are welcome for educational improvement and experimentation.

Suggested workflow:

```bash
git checkout -b feature/your-feature-name
git add .
git commit -m "Add your feature"
git push origin feature/your-feature-name
```

Then open a Pull Request with:

- A clear description of the change
- Screenshots for frontend changes
- Testing notes
- Any required environment variable updates

---

## 📄 License

This project is currently documented as an **educational university IoT project**.

If you intend to make it open-source for public reuse, add a license file such as:

- MIT License
- Apache License 2.0
- GPLv3

Until a license is added, reuse rights are not formally defined.

---

## 👨‍💻 Author

**Yonas Yifter**  
GitHub: [@yonasyifter](https://github.com/yonasyifter)

---

<div align="center">

### 🌲 Built for smarter, safer, and more data-driven natural park monitoring.

**If this project helps you, consider giving it a ⭐ on GitHub.**

</div>
