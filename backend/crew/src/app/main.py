"""
app/main.py
FastAPI entry point — Smart Park IoT + AI backend.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

sys.path.insert(0, os.path.dirname(__file__))

from app.config import GROQ_API_KEY, OPENROUTER_API_KEY
from app.database import init_firebase
from app.routes.auth import router as auth_router
from app.routes.crew import router as crew_router
from app.routes.rag import router as rag_router
from app.routes.weather import router as weather_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    active = []
    if GROQ_API_KEY:      active.append("Groq")
    if OPENROUTER_API_KEY: active.append("OpenRouter")
    providers = ", ".join(active) if active else "NONE — set GROQ_API_KEY or OPENROUTER_API_KEY"
    print(f"INFO: LLM providers: {providers}")
    yield


app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    title="Smart Park IoT + AI API",
    version="3.0.0",
    description="FastAPI backend with direct litellm multi-provider AI (Groq + OpenRouter fallback).",
    docs_url="/",
    redoc_url="/redoc",
)

_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
_ORIGINS = [o.strip().strip('"').strip("'") for o in _ORIGINS if o and o.strip()]

# If no origins provided via env, allow common dev ports for local development
if not _ORIGINS:
    _ORIGINS = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.amazonaws\.com)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(weather_router, prefix="/api/weather", tags=["Weather"])
app.include_router(crew_router,    prefix="/api/crew",    tags=["AI Assistant"])
app.include_router(rag_router,     prefix="/api/rag",     tags=["RAG Assistant"])


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    from crew.src.llm_router import list_providers
    return {"status": "ok", "version": "3.0.0", "llm_providers": list_providers()}


from mangum import Mangum
handler = Mangum(app, lifespan="off")
