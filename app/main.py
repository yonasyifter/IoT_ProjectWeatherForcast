# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from contextlib import asynccontextmanager
from routes.weather import router as weather_router
from routes.rag import router as rag_router # New RAG route
import os
import google.generativeai as genai
from config import GEMINI_API_KEY

# 1. Lifespan for efficient startup/shutdown (e.g., closing DB pools)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Gemini client or DB connections here
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    yield
    # Shutdown: Clean up resources

# 2. Use ORJSONResponse for faster JSON serialization
app = FastAPI(docs_url="/", redoc_url=None, title="IoT Weather API", version="1.0.0")

# 3. Secure CORS: Dynamic origins from environment variables
# Avoid "*" in production; explicitly list trusted domains
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173, http://192.168.0.1:8086").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)

# 4. Structured Routing
app.include_router(weather_router)
app.include_router(rag_router, prefix="/api/rag", tags=["AI Assistant"])

# 5. Lightweight Health Check
@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "version": "1.1.0"}