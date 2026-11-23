param(
    [string]$PiUrl = "http://raspberrypi.local:8011"
)

$ErrorActionPreference = "Stop"
$env:PI_SERVER_URL = $PiUrl.TrimEnd("/")
Set-Location $PSScriptRoot
python -m uvicorn app:app --host 0.0.0.0 --port 8010
