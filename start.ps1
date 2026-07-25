# Ozz CTF Universe Startup Script for PowerShell

Write-Host "🏴 Starting Ozz CTF Universe & Scoreboard..." -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

$env:PYTHONUTF8=1

$port9090 = Get-NetTCPConnection -LocalPort 9090 -ErrorAction SilentlyContinue
if (-not $port9090) {
    Write-Host "▶ Starting Scoreboard on http://localhost:9090..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "universe/scoreboard/server.py" -WindowStyle Hidden
} else {
    Write-Host "✔ Scoreboard is already running on http://localhost:9090" -ForegroundColor Cyan
}

Write-Host "▶ Starting Docker universe containers..." -ForegroundColor Yellow
wsl bash -c "sudo systemctl start docker; cd '/mnt/c/Users/Daniel Palma/Documents/antigravity/clever-pythagoras/ozz-halctf/universe'; sudo docker compose up -d"

Write-Host ""
Write-Host "✅ Ozz Universe is ready!" -ForegroundColor Green
Write-Host "-------------------------------------------" -ForegroundColor Gray
Write-Host "  Scoreboard:                http://localhost:9090" -ForegroundColor Green
Write-Host "  Target-01 (Web LFI/SQLi):  http://localhost:8081" -ForegroundColor Cyan
Write-Host "  Target-02 (SSH/SMB):      localhost:2222 / localhost:4455" -ForegroundColor Cyan
Write-Host "  Target-03 (Flask API):     http://localhost:5000" -ForegroundColor Cyan
Write-Host "-------------------------------------------" -ForegroundColor Gray
