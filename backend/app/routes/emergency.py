from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request


router = APIRouter(prefix="")

EMERGENCY_API_URL = "https://l6wlyfij89.execute-api.eu-north-1.amazonaws.com/prod/admin/emergency"
REQUEST_TIMEOUT_SECONDS = 15


def _raise_for_upstream_error(response: requests.Response) -> None:
    if response.ok:
        return

    try:
        payload: Any = response.json()
    except ValueError:
        payload = response.text or response.reason

    detail = payload.get("message") if isinstance(payload, dict) else payload
    if not detail:
        detail = f"Emergency API returned {response.status_code}"

    raise HTTPException(status_code=response.status_code, detail=detail)


@router.get("")
def get_emergency_requests():
    try:
        response = requests.get(EMERGENCY_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Emergency API request failed: {exc}") from exc

    _raise_for_upstream_error(response)
    return response.json()


@router.post("/resolve")
async def resolve_emergency_request(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        payload = {}

    try:
        response = requests.post(
            f"{EMERGENCY_API_URL}/resolve",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Emergency resolve request failed: {exc}") from exc

    _raise_for_upstream_error(response)
    return response.json() if response.content else {"resolved": True}
