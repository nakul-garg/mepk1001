# TA6 Cube Solver

TA6 is a five-motor Rubik's Cube robot. The Raspberry Pi runs the Kociemba two-phase solver and robot API. A laptop runs the dashboard and forwards requests to the Pi. Kociemba finds short practical solutions but does not guarantee the mathematically shortest solution for every state.

## Current status

- The dashboard has a 3D cube, mouse turns, random/custom scrambles, and multiple candidate routes ranked by an estimated time or move count.
- The Pi can solve a supplied 54-sticker facelet string in URFDLB order and reject impossible states.
- The first laptop server to contact the Pi claims it while the Pi solver process is running. Restarting the Pi solver releases that claim.
- Camera recognition is a calibration scaffold only. Real MKS/TMC motor control is not configured; the executor remains dry-run. There is no top-face motor, so U turns require a regrip.

## Requirements

- Current Raspberry Pi OS with Python 3. The Pi solver uses the standard library and bundled solver; no pip install is needed on the Pi.
- A Windows laptop with Git and Python 3.10 or newer.
- Pi and laptop on the same reachable local network. Enable SSH on the Pi for the copy instructions below.
- Allow the laptop dashboard through Windows Firewall on a Private network if prompted. Laptop dashboard port is 8010; Pi API port is 8011.

## Set up a new laptop

Open PowerShell and clone TA6:

```powershell
git clone https://github.com/nakul-garg/mepk1001.git TA6
cd TA6
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r laptop_server\requirements.txt
```

If PowerShell blocks environment activation, run the setup commands in a new PowerShell window or use .venv\Scripts\python.exe explicitly in the server command below.

## Copy and start the Raspberry Pi solver

Copy the whole raspberry_pi folder from the TA6 repository. Do not omit vendor/pure_python or its .pkl pruning tables. From the TA6 root on Windows PowerShell:

```powershell
scp -r .\raspberry_pi pi@raspberrypi.local:~/
```

Replace raspberrypi.local with the Pi's IP address if name lookup does not work. On the Pi terminal (or over SSH):

```bash
cd ~/raspberry_pi
bash setup.sh
./run_solver.sh
```

Leave this process running. It listens on port 8011. Find the Pi address with hostname -I. No Pi packages or robot ID are required. To release the first-laptop lock, stop the process with Ctrl+C and start it again with ./run_solver.sh.

## Start the laptop dashboard

Replace the example address with the Pi address. In PowerShell at the TA6 repository root:

```powershell
$env:PI_SERVER_URL = "http://192.168.1.50:8011"
Set-Location .\laptop_server
..\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8010
```

Alternatively, with the virtual environment active, enter laptop_server and run:

```powershell
.\start_server.ps1 -PiUrl http://192.168.1.50:8011
```

The first laptop server to reach the Pi claims it. Other laptop servers are rejected until the Pi solver restarts. Open http://localhost:8010/ on the laptop. If the Pi address changes, stop and restart the laptop server with its new address.

## Camera scan variables and pixel calibration

The scaffold is raspberry_pi/camera_scan.py. It intentionally contains no guessed pixel coordinates or color calibration. When camera placement is finalized, fill SAMPLE_PIXEL_COORDINATES with named sticker-center locations and COLOR_REFERENCE_RGB with measured color references. Raw samples are retained by sticker name in scan_rgb_variables (for example F5); classified letters are retained in facelet_color_variables. The pixel reader is passed in, so the camera library can be selected once you share the camera model.

A fixed diagonal camera view sees only three faces at once. To read all 54 stickers, the robot will need calibrated additional views using a regrip/rotation sequence, or another observation method. Camera model, sticker orientation, exact pixels, and the regrip sequence are still needed before automatic scanning can run.

## Project folders

- laptop_server: dashboard, Pi proxy, and Windows launcher.
- raspberry_pi/solver_app.py: standard-library API and Pi-local solver.
- raspberry_pi/camera_scan.py: named pixel and color variables awaiting calibration.
- raspberry_pi/robot_executor.py: five-motor contract and dry-run scaffold.
- server: earlier laptop-local solver retained for reference.

## Hardware integration still needed

The executor will not actuate the MKS Gen I v1 or TMC2209 yet. Confirm motor-to-face assignments, end stops/sensors, UART addresses/settings, steps per quarter-turn, gripping, and regrip orientation tracking before configuring it. Keep the fifth motor for the regrip/access mechanism; do not add a top motor.
