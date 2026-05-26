# setup-dev.ps1
# Usage: powershell -ExecutionPolicy Bypass -File .\setup-dev.ps1
# Requires: Docker Desktop

$ErrorActionPreference = "Stop"

function Write-Step($n, $msg) {
    Write-Host ""
    Write-Host "  [$n] $msg"
}
function Write-OK($msg)   { Write-Host "  [OK]   $msg" }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" }

Write-Host ""
Write-Host "========================================"
Write-Host "  AirGuard Pi - Dev Environment Setup"
Write-Host "========================================"
Write-Host ""

# Step 1: Check Docker
Write-Step 1 "Check Docker Desktop"
try {
    $v = docker --version 2>&1
    Write-OK $v
} catch {
    Write-Fail "Docker not found. Install from https://docker.com/products/docker-desktop"
    exit 1
}

# Step 2: Create .env
Write-Step 2 "Create .env from .env.dev"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.dev" ".env"
    Write-OK ".env created"
} else {
    Write-Warn ".env already exists - skipping"
}

# Step 3: Build and start services
Write-Step 3 "Build and start services (first run may take 2-5 min)"
Write-Host "  Services: InfluxDB, Mosquitto, Backend, Frontend, Grafana"
Write-Host ""

docker compose -f docker-compose.dev.yml up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Fail "docker compose failed - check errors above"
    exit 1
}
Write-OK "Services started"

# Step 4: Wait for backend
Write-Step 4 "Waiting for backend (max 60s)"
$ready = $false
for ($i = 1; $i -le 12; $i++) {
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "  ...waiting ($($i*5)s)"
}

if (-not $ready) {
    Write-Warn "Backend not ready - check logs: docker compose -f docker-compose.dev.yml logs backend"
} else {
    Write-OK "Backend ready"
}

# Step 5: Summary
Write-Host ""
Write-Host "========================================"
Write-Host "  Dev Environment Ready!"
Write-Host "========================================"
Write-Host ""
Write-Host "  Dashboard -> http://localhost:5173"
Write-Host "  API Docs  -> http://localhost:8000/docs"
Write-Host "  InfluxDB  -> http://localhost:8086  (admin / adminpass123)"
Write-Host "  Grafana   -> http://localhost:3001  (admin / admin)"
Write-Host "  MQTT      -> localhost:1883"
Write-Host ""
Write-Host "  Next steps:"
Write-Host "  1. Open a new terminal and run:"
Write-Host "     python mock_sensor.py --scenario full --interval 3"
Write-Host "  2. Test the pipeline:"
Write-Host "     python test_pipeline.py"
Write-Host "  3. View live logs:"
Write-Host "     docker compose -f docker-compose.dev.yml logs -f backend"
Write-Host ""
