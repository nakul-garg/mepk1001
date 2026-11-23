# Rubik's Cube Solver (laptop + Raspberry Pi)

This project puts the search on the laptop and exposes a small HTTP API for the Pi. It uses Kociemba's two-phase solver, which produces short practical solutions but does **not** guarantee the mathematical shortest solution for every scramble. The vendored pure-Python fallback avoids requiring a C++ compiler, but runs slower than the native extension.

## Laptop server

From `server/`, install `requirements.txt`, then run:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8010
```

Open `http://LAPTOP_IP:8010/` for the cube dashboard. It renders the current facelets on an animated 3D model, creates virtual scrambles, accepts mouse face turns, requests a solution, and reads the latest Pi scan. Click a visible face for a clockwise turn, right-click for counterclockwise; the picked face is determined from the 3D camera ray and cube rotation. The Pi can publish a scan with `upload_scanned_state(server, facelets)` from `raspberry_pi/client.py`; the camera capture and color calibration pipeline still needs to be connected for your camera.

The Pi sends `POST /solve` with JSON `{"facelets":"...54 letters..."}`. Facelets are ordered U, R, F, D, L, B, nine stickers per face, and each letter denotes the color of that face's center sticker. The response includes standard Singmaster notation and a move count. `POST /validate` checks the same input and returns whether it is physically solvable. It rejects bad color counts and cube states that violate piece, orientation, or parity constraints. Keep the laptop and Pi on the same trusted network.

## Raspberry Pi

Run `python client.py http://LAPTOP_IP:8000 FACELETS` from `raspberry_pi/`. `robot_executor.py` is a five-motor execution scaffold with no top-face motor. It remains dry-run only until the MKS firmware protocol, motor-to-mechanism mapping, and regrip choreography are configured. The motor labels in this file are limited to IDs 0 through 4.

## Camera scanning

A camera view showing three adjacent faces can capture half the stickers at once. The cube can then be reoriented to expose the other three faces; the scan algorithm must track each reorientation so every observation is assigned to the correct face and sticker index. A complete scan still needs calibrated camera geometry and color classification. After each view, the vision code maps observed colors to center-relative U/R/F/D/L/B facelets, then submits the assembled 54-character state. The `/validate` endpoint can flag a scan that is inconsistent or physically impossible before movement.

## Deployment status

This is not yet a copy-and-run robot image: the server API and animated cube UI work independently, but camera scanning and MKS motor actuation are still hardware-specific integration points. The Raspberry Pi should run the camera/control client while the laptop server stays on the laptop, matching the selected architecture. If you want the solver to run on the Pi instead, install the same server requirements there and run the API on the Pi.

The MKS board revision must be confirmed. MKS describes Gen_L V2.x as supporting onboard TMC2209 UART; the Gen_L V1.0 hardware is listed separately. UART-capable drivers alone do not tell us how your particular board is wired or what firmware is running.

## Needed to finish the robot integration

Please share: (1) what each of the five motors mechanically rotates or presses and whether a motor can turn a face both directions; (2) MKS Monster board revision, driver models, motor wiring and firmware/control interface; (3) camera model, mounting angle/distance, lighting, and how you plan to expose all six faces; (4) Raspberry Pi model and preferred connection to laptop (Wi-Fi/Ethernet/USB); (5) whether the scramble is random legal turns or arbitrary manual states. These determine scan choreography and how to translate solver moves to reliable motor commands.
