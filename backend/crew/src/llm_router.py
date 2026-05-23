"""
crew/src/llm_router.py

Multi-provider LLM router using litellm directly.

Priority order:
  1. AWS Bedrock  (Claude Sonnet — decoded from AWS_BEDROCK env var)
  2. Groq         (llama-3.3-70b-versatile — fast free-tier fallback)
  3. OpenRouter   (set OPENROUTER_API_KEY in .env to enable)

Used by the direct-call path in routes/crew.py (non-agent chatbot).
The CrewAI agent path (crew.py) uses _make_llm() directly.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import litellm

litellm.telemetry = False
litellm.set_verbose = False

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Bedrock credential decoding
# ─────────────────────────────────────────────────────────────────────────────

def _decode_bedrock_key(raw: str) -> tuple[str, str]:
    """Decode base64 AWS_BEDROCK → (access_key_id, secret_access_key)."""
    try:
        if raw.startswith("ABSK"):
            raw = raw[4:]
        decoded = base64.b64decode(raw).decode("utf-8")
        if decoded.startswith("BedrockAPIKey-"):
            decoded = decoded[len("BedrockAPIKey-"):]
        parts = decoded.split(":", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    except Exception as exc:
        logger.warning("Bedrock key decode failed: %s", exc)
    return "", ""


_RAW_BEDROCK = os.getenv(
    "AWS_BEDROCK",
    "ABSKQmVkcm9ja0FQSUtleS15Mmd5LWF0LTI4OTQwMDg1NDY5MTpiRFhoWG1QaFBBdDBwZVhoM0QxeGdGMjVWcU1CU2ZDRjZMbFk3eXlEZW9wWW0zWml2Z2FvK01PMDhjOD0="
)
_BEDROCK_AKI, _BEDROCK_SECRET = _decode_bedrock_key(_RAW_BEDROCK)
_BEDROCK_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Inject into environment so litellm can auto-pick them up
if _BEDROCK_AKI:
    os.environ["AWS_ACCESS_KEY_ID"]     = _BEDROCK_AKI
    os.environ["AWS_SECRET_ACCESS_KEY"] = _BEDROCK_SECRET
    os.environ["AWS_DEFAULT_REGION"]    = _BEDROCK_REGION


# ─────────────────────────────────────────────────────────────────────────────
# Provider registry
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProviderConfig:
    name: str
    model: str
    api_key_env: str
    default_key: str = ""
    base_url: Optional[str] = None
    extra_headers: dict = field(default_factory=dict)
    # AWS-specific fields
    aws_aki: str = ""
    aws_secret: str = ""
    aws_region: str = ""


PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        name="Groq (llama-3.3-70b)",
        model="groq/llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY2",
        default_key="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",
    ),
    # ── 2. Groq (fast free-tier) ─────────────────────────────────────────────
    ProviderConfig(
        name="Groq (llama-3.3-70b)",
        model="groq/llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
        default_key="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",
    ),
# ── 3. OpenRouter (optional) ─────────────────────────────────────────────

    ProviderConfig(
        name="OpenRouter (llama-3.3-70b)",
        model="openrouter/meta-llama/llama-3.3-70b-instruct",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        extra_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "SmartPark",
        },
    ),

    ProviderConfig(
        name="OpenRouter (mistral-7b free)",
        model="openrouter/mistralai/mistral-7b-instruct:free",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        extra_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "SmartPark",
        },
    ),
]


def _get_key(p: ProviderConfig) -> str:
    # For Bedrock, key presence is checked via aws_aki
    if p.aws_aki:
        return p.aws_aki
    return os.getenv(p.api_key_env, p.default_key).strip()


def call_llm(messages: list[dict], timeout: int = 60) -> str:
    """
    Try each provider in order.
    Returns text from the first provider that succeeds.
    Raises RuntimeError if all fail.
    """
    errors: list[str] = []

    for provider in PROVIDERS:
        key = _get_key(provider)
        if not key:
            errors.append(f"{provider.name}: no key ({provider.api_key_env} not set)")
            continue

        print(f"[LLM Router] Trying: {provider.name}")
        kwargs: dict = dict(
            model=provider.model,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            timeout=timeout,
        )

        # AWS Bedrock uses IAM credentials, not an API key header
        if provider.aws_aki:
            kwargs["aws_access_key_id"]     = provider.aws_aki
            kwargs["aws_secret_access_key"] = provider.aws_secret
            kwargs["aws_region_name"]       = provider.aws_region
        else:
            kwargs["api_key"] = key

        if provider.base_url:
            kwargs["base_url"] = provider.base_url
        if provider.extra_headers:
            kwargs["extra_headers"] = provider.extra_headers

        try:
            response = litellm.completion(**kwargs)
            text = response.choices[0].message.content or ""
            print(f"[LLM Router] OK: {provider.name} responded ({len(text)} chars)")
            return text.strip()
        except Exception as exc:
            msg = f"{provider.name}: {type(exc).__name__}: {exc}"
            logger.warning("[LLM Router] %s", msg)
            print(f"[LLM Router] FAIL: {msg}")
            errors.append(msg)

    raise RuntimeError(
        "All LLM providers failed:\n" + "\n".join(f"  - {e}" for e in errors)
    )


def list_providers() -> list[dict]:
    """Return provider status — used by /health endpoint."""
    out = []
    for p in PROVIDERS:
        key = _get_key(p)
        out.append({
            "name": p.name,
            "model": p.model,
            "key_env": p.api_key_env,
            "key_set": bool(key),
            "key_preview": f"{key[:8]}..." if key else "(not set)",
        })
    return out