"""Laptop dashboard host that forwards solver calls to the Raspberry Pi."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.responses import FileResponse

app = FastAPI(title="TA6 Cube Dashboard", version="0.2.0")
PI_SERVER_URL = os.environ.get("PI_SERVER_URL", "http://raspberrypi.local:8011").rstrip("/")


def pi_request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{PI_SERVER_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except (ValueError, AttributeError):
            pass
        raise HTTPException(exc.code, str(detail)) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise HTTPException(502, f"Cannot reach the Raspberry Pi solver at {PI_SERVER_URL}: {exc}") from exc


def forward(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    # Pi claims the first laptop proxy to contact /health, then accepts only that source IP.
    if path != "/health":
        pi_request("/health")
    return pi_request(path, method, payload)


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/health")
def health() -> dict:
    try:
        pi = pi_request("/health")
    except HTTPException as exc:
        return {"status": "unavailable", "connected": False, "error": exc.detail}
    return {"status": "ok", "connected": True, "pi_solver": pi}


@app.get("/state")
def get_state() -> dict:
    return forward("/state")


@app.post("/state")
async def set_state(request: FastAPIRequest) -> dict:
    return forward("/state", "POST", await request.json())


@app.post("/solve")
async def solve(request: FastAPIRequest) -> dict:
    return forward("/solve", "POST", await request.json())


@app.post("/validate")
async def validate(request: FastAPIRequest) -> dict:
    return forward("/validate", "POST", await request.json())
