from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .routes.weather import router as weather_router

app = FastAPI(docs_url="/", redoc_url=None, title="IoT Weather API", version="1.0.0")

# CORS: allow Vite dev server (and localhost) during development
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static frontend (index.html) from app/static
app.mount("/index", StaticFiles(directory="app/static", html=True), name="static")

app.include_router(weather_router)


@app.get("/a", include_in_schema=False)
def health():
    return 0
