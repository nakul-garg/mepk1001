"""Raspberry Pi-local Kociemba solver API using only the Python stdlib."""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

VENDORED_SOLVER = Path(__file__).parent / "vendor" / "pure_python"
sys.path.insert(0, str(VENDORED_SOLVER))
import kociemba  # noqa: E402 (vendored module path must be added first)

FACE_ORDER = "URFDLB"
latest_state: str | None = None
state_lock = threading.Lock()
connected_client_ip: str | None = None
connection_lock = threading.Lock()


class CubeAPI(BaseHTTPRequestHandler):
    server_version = "CubePi/0.2"

    def _reply(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError("request body size must be between 1 and 8192 bytes")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            return data
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid JSON request: {exc}") from exc

    def _cube_state(self, data: dict) -> str:
        facelets = data.get("facelets")
        if not isinstance(facelets, str):
            raise ValueError("facelets must be a string")
        state = facelets.upper().replace(" ", "")
        if len(state) != 54 or any(letter not in FACE_ORDER for letter in state):
            raise ValueError("facelets must be 54 letters from URFDLB")
        counts = {face: state.count(face) for face in FACE_ORDER}
        if any(count != 9 for count in counts.values()):
            raise ValueError(f"each face letter must occur 9 times; got {counts}")
        return state

    def _claim_or_check_client(self) -> bool:
        global connected_client_ip
        source_ip = self.client_address[0]
        with connection_lock:
            if connected_client_ip is None:
                connected_client_ip = source_ip
            return connected_client_ip == source_ip

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/health":
            if not self._claim_or_check_client():
                self._reply(409, {"detail": "This Raspberry Pi is already connected to its first laptop. Restart the Pi solver to release the connection."})
                return
            self._reply(200, {
                "status": "ok",
                "solver": "kociemba-two-phase",
                "location": "raspberry-pi",
                "connected": True,
                "client_ip": connected_client_ip,
            })
        elif route == "/state":
            if not self._claim_or_check_client():
                self._reply(409, {"detail": "This Raspberry Pi is already connected to its first laptop."})
                return
            with state_lock:
                state = latest_state
            if state is None:
                self._reply(404, {"detail": "No cube scan has been uploaded yet"})
            else:
                self._reply(200, {"facelets": state})
        else:
            self._reply(404, {"detail": "Not found"})

    def do_POST(self) -> None:
        global latest_state
        route = urlparse(self.path).path
        if not self._claim_or_check_client():
            self._reply(409, {"detail": "This Raspberry Pi is already connected to its first laptop."})
            return
        try:
            state = self._cube_state(self._read_json())
        except ValueError as exc:
            self._reply(422, {"detail": str(exc)})
            return

        if route == "/state":
            with state_lock:
                latest_state = state
            self._reply(200, {"saved": True, "facelets": state})
            return

        if route not in {"/solve", "/validate"}:
            self._reply(404, {"detail": "Not found"})
            return
        try:
            notation = kociemba.solve(state)
        except Exception as exc:
            self._reply(422, {"detail": f"Impossible or invalid cube state: {exc}"})
            return

        if route == "/validate":
            self._reply(200, {"valid": True, "facelets": state, "message": "Cube state is physically solvable"})
        else:
            moves = notation.split() if notation else []
            self._reply(200, {"facelets": state, "notation": notation, "moves": moves, "move_count": len(moves)})

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    host, port = "0.0.0.0", 8011
    print(f"Cube solver on http://{host}:{port} — first laptop connection is exclusive")
    ThreadingHTTPServer((host, port), CubeAPI).serve_forever()
