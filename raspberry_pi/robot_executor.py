"""Five-motor solution executor scaffold for the Raspberry Pi.

The solver notation is fixed to the cube's logical U/R/F/D/L/B frame. This
module deliberately has no U-face motor. A hardware adapter must implement
U turns through the robot's regrip mechanism (using its fifth motor) while
preserving the logical cube frame. Exact MKS Monster/driver commands belong
in that adapter once the board and mechanism are known.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen

FACES = frozenset("URFDLB")
MOTOR_COUNT = 5


@dataclass(frozen=True)
class Move:
    face: str
    quarter_turns: int  # 1 clockwise, -1 counterclockwise, 2 half turn

    @classmethod
    def parse(cls, token: str) -> "Move":
        if not token or token[0] not in FACES or len(token) > 2:
            raise ValueError(f"Invalid Singmaster move: {token!r}")
        suffix = token[1:]
        if suffix == "":
            turns = 1
        elif suffix == "'":
            turns = -1
        elif suffix == "2":
            turns = 2
        else:
            raise ValueError(f"Invalid Singmaster suffix in {token!r}")
        return cls(token[0], turns)


class FiveMotorHardware(Protocol):
    """Physical adapter contract. motor_id is always in [0, 4]."""

    def turn_face(self, motor_id: int, quarter_turns: int) -> None: ...

    def regrip_to_access(self, logical_face: str) -> int:
        """Position/reorient cube and return a motor ID able to turn that face.

        Must use the fifth motor/regrip mechanism as needed, keep track of cube
        orientation, and never return a sixth motor. This makes no assumption
        that the U face itself has a motor.
        """
        ...

    def release_all(self) -> None: ...


class FiveMotorExecutor:
    def __init__(self, hardware: FiveMotorHardware, move_delay_s: float = 0.15):
        self.hardware = hardware
        self.move_delay_s = move_delay_s

    def execute(self, notation: str | list[str]) -> None:
        tokens = notation.split() if isinstance(notation, str) else notation
        moves = [Move.parse(token) for token in tokens]
        try:
            for move in moves:
                # Always ask the orientation-aware adapter. In particular, U
                # is serviced by regripping and one of the other five motors.
                motor_id = self.hardware.regrip_to_access(move.face)
                if not isinstance(motor_id, int) or not 0 <= motor_id < MOTOR_COUNT:
                    raise RuntimeError(f"Adapter returned invalid motor ID {motor_id!r}; only 0-4 exist")
                self.hardware.turn_face(motor_id, move.quarter_turns)
                if self.move_delay_s:
                    time.sleep(self.move_delay_s)
        except Exception:
            # Leave actuators in a known disabled state after a partial failure.
            self.hardware.release_all()
            raise
        self.hardware.release_all()


class DryRunHardware:
    """Safe placeholder that logs actions; replace with an MKS-specific adapter."""

    def regrip_to_access(self, logical_face: str) -> int:
        # Demonstration only: all faces map to motor 0. The U request is still
        # routed through this regrip hook, never to a dedicated U motor.
        print(f"REGRIP: position logical {logical_face} for an available face motor")
        return 0

    def turn_face(self, motor_id: int, quarter_turns: int) -> None:
        if motor_id == 0:
            print(f"DRY RUN: motor {motor_id} turns face {quarter_turns:+d} quarter-turn(s)")

    def release_all(self) -> None:
        print("RELEASE: all motor outputs disabled")


def fetch_solution(server: str, facelets: str) -> list[str]:
    body = json.dumps({"facelets": facelets}).encode("utf-8")
    request = Request(server.rstrip("/") + "/solve", data=body,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["moves"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("facelets", help="54 facelets in server URFDLB format")
    parser.add_argument("--server", required=True, help="Laptop URL, e.g. http://192.168.1.20:8000")
    parser.add_argument("--execute", action="store_true", help="Enable the configured hardware adapter")
    args = parser.parse_args()
    solution = fetch_solution(args.server, args.facelets)
    print("Server solution:", " ".join(solution))
    if args.execute:
        raise SystemExit("No MKS hardware adapter configured yet; refusing to actuate motors")
    FiveMotorExecutor(DryRunHardware()).execute(solution)
