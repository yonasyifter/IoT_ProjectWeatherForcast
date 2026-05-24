"""
Server-side proxy for Robustel RCMS Open API.

The RCMS API uses HMAC headers and generally should not be called directly
from the browser. This route keeps the secret server-side and avoids CORS
failures in the Vue RCMS pages.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from typing import Any, Literal

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.routes.auth import get_admin_session_user


router = APIRouter()
LOGGER = logging.getLogger(__name__)

RCMS_BASE = os.getenv("RCMS_BASE", "https://rcms-cloud.robustel.net").rstrip("/")
RCMS_CLIENT_ID = os.getenv("RCMS_CLIENT_ID", "230c0f5b40354b4eb3f9d0eb5a9199cf")
RCMS_CLIENT_SECRET = os.getenv("RCMS_CLIENT_SECRET", "")
RCMS_TIMEOUT = int(os.getenv("RCMS_TIMEOUT_SECONDS", "20"))


class RcmsProxyRequest(BaseModel):
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str = Field(..., min_length=1)
    queryParams: dict[str, Any] = Field(default_factory=dict)
    body: Any = None


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None and value != ""}


def _json_body(body: Any) -> str:
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False)


def _headers(method: str, path: str, params: dict[str, Any], body: Any) -> dict[str, str]:
    if not RCMS_CLIENT_ID or not RCMS_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="RCMS OpenAPI is not configured. Set RCMS_CLIENT_ID and RCMS_CLIENT_SECRET in backend/.env.",
        )

    timestamp = str(int(__import__("time").time() * 1000))
    unique_code = str(uuid.uuid4())
    public_params = {
        "apiVersion": "1.0",
        "clientId": RCMS_CLIENT_ID,
        "signatureVersion": "1.0",
        "timestamp": timestamp,
        "uniqueCode": unique_code,
        **params,
    }
    canonical = "&".join(f"{key}={public_params[key]}" for key in sorted(public_params))

    string_to_sign = f"{method.upper()}{path}{canonical}"
    if body is not None:
        string_to_sign += f"&{_json_body(body)}"
    string_to_sign += RCMS_CLIENT_SECRET

    signature_key = f"{RCMS_CLIENT_ID}{unique_code}".encode("utf-8")
    signature = hmac.new(signature_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    return {
        "clientId": RCMS_CLIENT_ID,
        "signatureVersion": "1.0",
        "apiVersion": "1.0",
        "timestamp": timestamp,
        "uniqueCode": unique_code,
        "signature": signature,
        "Content-Type": "application/json",
    }


def _error_detail(path: str, data: dict[str, Any]) -> str:
    code = data.get("code")
    msg = data.get("msg") or data.get("message") or "failure"
    detail = f"RCMS {code}: {msg}"
    if code == -1 and path == "/api/gm/devices":
        detail += (
            ". RCMS rejected the device registration. Verify that SN and IMEI/MAC "
            "belong to the same Robustel device, the model matches the serial number, "
            "the RCMS Device Area is sent as an RCMS code (EUR, EA, EA2, NA, SA, AU), "
            "and the device is not already bound to another account."
        )
    return detail


@router.post("/request", dependencies=[Depends(get_admin_session_user)])
def rcms_request(payload: RcmsProxyRequest) -> Any:
    method = payload.method.upper()
    path = payload.path.strip()
    if not path.startswith("/api/") or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid RCMS API path.")

    params = _clean_params(payload.queryParams)
    body = payload.body
    headers = _headers(method, path, params, body)

    try:
        response = requests.request(
            method,
            f"{RCMS_BASE}{path}",
            params=params,
            data=_json_body(body) if body is not None else None,
            headers=headers,
            timeout=RCMS_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"RCMS request failed: {exc}") from exc

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=f"RCMS HTTP {response.status_code}: {response.text[:500]}")

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="RCMS returned non-JSON response.") from exc

    if isinstance(data, dict) and data.get("code") not in (None, 0):
        LOGGER.warning("RCMS rejected %s %s with response: %s", method, path, data)
        raise HTTPException(status_code=502, detail=_error_detail(path, data))

    return data.get("data") if isinstance(data, dict) and "data" in data else data
