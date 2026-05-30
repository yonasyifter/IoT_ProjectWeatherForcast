import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)

# INFLUXDB Configuration
INFLUXDB_URL         = os.getenv("INFLUXDB_URL", "")
INFLUXDB_TOKEN       = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG         = os.getenv("INFLUXDB_ORG", "")
INFLUXDB_BUCKET      = os.getenv("INFLUXDB_BUCKET", "")
INFLUXDB_MEASUREMENT = os.getenv("INFLUXDB_MEASUREMENT", "")
INFLUXDB_MEASUREMENT2 = os.getenv("INFLUXDB_MEASUREMENT2", "digitalTwinCommand")
INFLUXDB_MEASUREMENT3 = os.getenv("INFLUXDB_MEASUREMENT3", "Ack2digitalTwin")
INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT = os.getenv(
    "INFLUXDB_DIGITAL_TWIN_DELETED_MEASUREMENT",
    "DeletedDigitalTwinAlert",
)

# ── LLM Provider API Keys ──────────────────────────────────────────────────
# At least one of these must be set. The router tries them in order:
#   1. Groq  →  2. OpenRouter
GROQ_API_KEY        = os.getenv("GROQ_API_KEY",
                          "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")
GROQ_MODEL_ID       = os.getenv("GROQ_MODEL_ID", "groq/llama-3.3-70b-versatile")

OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")   # set in .env to enable
OPENROUTER_MODEL_ID = os.getenv("OPENROUTER_MODEL_ID",
                          "openrouter/meta-llama/llama-3.3-70b-instruct")

# Firebase Configuration
FIREBASE_PROJECT_ID    = os.getenv("FIREBASE_PROJECT_ID", "iot-project-49099")
FIREBASE_PRIVATE_KEY_ID= os.getenv("FIREBASE_PRIVATE_KEY_ID", "")
FIREBASE_PRIVATE_KEY   = os.getenv("FIREBASE_PRIVATE_KEY", "")
FIREBASE_CLIENT_EMAIL  = os.getenv(
    "FIREBASE_CLIENT_EMAIL",
    "firebase-adminsdk@iot-project-49099.iam.gserviceaccount.com")
FIREBASE_CLIENT_ID     = os.getenv("FIREBASE_CLIENT_ID", "")
FIREBASE_CERT_URL      = os.getenv("FIREBASE_CERT_URL", "")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

def validate_config() -> None:
    # At least one LLM key required
    if not GROQ_API_KEY and not OPENROUTER_API_KEY:
        raise RuntimeError(
            "No LLM API key configured. Set GROQ_API_KEY or OPENROUTER_API_KEY in .env"
        )

    missing = [k for k, v in {
        "INFLUXDB_URL":            INFLUXDB_URL,
        "INFLUXDB_TOKEN":          INFLUXDB_TOKEN,
        "INFLUXDB_ORG":            INFLUXDB_ORG,
        "INFLUXDB_BUCKET":         INFLUXDB_BUCKET,
        "INFLUXDB_MEASUREMENT":    INFLUXDB_MEASUREMENT,
        "FIREBASE_PROJECT_ID":     FIREBASE_PROJECT_ID,
        "FIREBASE_PRIVATE_KEY_ID": FIREBASE_PRIVATE_KEY_ID,
        "FIREBASE_PRIVATE_KEY":    FIREBASE_PRIVATE_KEY,
        "FIREBASE_CLIENT_EMAIL":   FIREBASE_CLIENT_EMAIL,
        "FIREBASE_CLIENT_ID":      FIREBASE_CLIENT_ID,
        "FIREBASE_CERT_URL":       FIREBASE_CERT_URL,
        "FIREBASE_CREDENTIALS_PATH": FIREBASE_CREDENTIALS_PATH,
    }.items() if not v]

    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
