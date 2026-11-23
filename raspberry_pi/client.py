"""Small Raspberry Pi client: submit a scanned cube and receive a solution."""
import argparse
import json
import urllib.error
import urllib.request


def solve_on_server(server: str, facelets: str) -> dict:
    url = server.rstrip("/") + "/solve"
    payload = json.dumps({"facelets": facelets}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Solver returned HTTP {exc.code}: {exc.read().decode('utf-8')}") from exc


def upload_scanned_state(server: str, facelets: str) -> dict:
    """Publish the Pi's latest camera scan for the dashboard's Read Pi button."""
    url = server.rstrip("/") + "/state"
    payload = json.dumps({"facelets": facelets}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", help="Laptop URL, e.g. http://192.168.1.20:8000")
    parser.add_argument("facelets", help="54 sticker colors encoded as URFDLB letters")
    args = parser.parse_args()
    print(json.dumps(solve_on_server(args.server, args.facelets), indent=2))
