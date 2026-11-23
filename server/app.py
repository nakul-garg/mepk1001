"""Laptop-side cube solving API.

Input facelets use Kociemba's URFDLB order, nine stickers per face.
"""
from __future__ import annotations

from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

VENDORED_SOLVER = Path(__file__).parent / "vendor" / "pure_python"
if VENDORED_SOLVER.is_dir():
    sys.path.insert(0, str(VENDORED_SOLVER))

try:
    import kociemba
except ImportError:  # Keep /health usable before dependencies are installed.
    kociemba = None

app = FastAPI(title="TA6 Cube Solver", version="0.1.0")
FACE_ORDER = "URFDLB"
latest_state: str | None = None


@app.get("/")
def interface() -> FileResponse:
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/state")
def get_state() -> dict:
    if latest_state is None:
        raise HTTPException(404, "No cube scan has been uploaded yet")
    return {"facelets": latest_state}




class SolveRequest(BaseModel):
    # 54 chars, facelets in URFDLB order. Center stickers identify each face.
    facelets: str = Field(min_length=54, max_length=54)


@app.post("/state")
def set_state(request: SolveRequest) -> dict:
    global latest_state
    latest_state = normalized_state(request.facelets)
    return {"saved": True, "facelets": latest_state}


def normalized_state(facelets: str) -> str:
    state = facelets.upper().replace(" ", "")
    if len(state) != 54 or any(c not in FACE_ORDER for c in state):
        raise HTTPException(422, "facelets must be 54 letters from URFDLB")
    counts = {face: state.count(face) for face in FACE_ORDER}
    if any(count != 9 for count in counts.values()):
        raise HTTPException(422, f"each face letter must occur 9 times; got {counts}")
    return state


def find_solution(state: str) -> str:
    if kociemba is None:
        raise HTTPException(503, "Install server requirements to enable solving")
    try:
        return kociemba.solve(state)
    except Exception as exc:
        # Solver rejects states that violate cube piece, orientation, or parity rules.
        raise HTTPException(422, f"Impossible or invalid cube state: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "solver": "ready" if kociemba else "dependency_missing"}


@app.post("/solve")
def solve(request: SolveRequest) -> dict:
    state = normalized_state(request.facelets)
    notation = find_solution(state)
    moves = notation.split() if notation else []
    return {"facelets": state, "notation": notation, "moves": moves, "move_count": len(moves)}


@app.post("/validate")
def validate(request: SolveRequest) -> dict[str, str | bool]:
    """Check that the scanned stickers describe a physically reachable cube."""
    state = normalized_state(request.facelets)
    find_solution(state)
    return {"valid": True, "facelets": state, "message": "Cube state is physically solvable"}
