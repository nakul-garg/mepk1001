#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required" >&2; exit 1; }
chmod +x run_solver.sh
echo "Pi solver ready. No pip packages are required."
echo "Start it with ./run_solver.sh"
