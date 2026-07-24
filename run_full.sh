#!/bin/bash
# ============================================
# 🏴 OZZ — Full Stack (Universe + Agent + LLM)
# Tudo rodando no mesmo Docker
# ============================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║  🏴 OZZ — FULL STACK LAUNCHER            ║"
echo "  ║  Universe + Agent + LLM                  ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check GPU
echo -e "${CYAN}Checking GPU...${NC}"
if nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null)
    echo -e "${GREEN}  ✅ GPU found: ${GPU_INFO}${NC}"
    HAS_GPU=true
else
    echo -e "${YELLOW}  ⚠️  No GPU detected. Agent will run with mock LLM.${NC}"
    echo -e "${YELLOW}     For real LLM, use Kaggle (scripts/ozz_kaggle.ipynb)${NC}"
    HAS_GPU=false
fi

# Start universe
echo ""
echo -e "${CYAN}Starting universe...${NC}"
cd "$SCRIPT_DIR/universe"
docker compose up -d --build 2>&1 | tail -3
sleep 3

# Start scoreboard
echo -e "${GREEN}  ✅ Universe running${NC}"
echo -e "  📊 Scoreboard: http://localhost:9090"

# Run agent
echo ""
if [ "$HAS_GPU" = true ]; then
    echo -e "${CYAN}Starting agent with GPU (real LLM)...${NC}"
    cd "$SCRIPT_DIR"
    docker build -t ozz:latest . 2>&1 | tail -3
    docker run --gpus all \
        --network host \
        -e TARGETS="10.0.0.10,10.0.0.20,10.0.0.30" \
        -e MODEL_NAME="Qwen/Qwen2.5-Coder-7B-Instruct" \
        -v ozz-models:/models \
        ozz:latest
else
    echo -e "${CYAN}Running mock agent (no GPU)...${NC}"
    cd "$SCRIPT_DIR"
    python3 scripts/mock_runner.py --scenario multi_target_parallel --verbose
fi

echo ""
echo -e "${GREEN}🏴 Done! Check scoreboard: http://localhost:9090${NC}"
