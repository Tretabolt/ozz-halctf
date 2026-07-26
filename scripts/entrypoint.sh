#!/bin/bash
# Ozz — Docker Entrypoint
# Starts vLLM model server and the agent

set -e

# Configuration
MODEL_PATH="${MODEL_PATH:-/models}"
MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-Coder-7B-Instruct}"
VLLM_PORT="${VLLM_PORT:-8000}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.85}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"

echo "🏴 =========================================="
echo "  OZZ — HALctf Autonomous Pentesting Agent"
echo "  DEF CON 34 AI Village"
echo "=========================================="
echo ""
echo "Model: $MODEL_NAME"
echo "Path: $MODEL_PATH"
echo "Port: $VLLM_PORT"
echo "GPU Memory: $GPU_MEMORY_UTILIZATION"
echo "Max Model Length: $MAX_MODEL_LEN"
echo ""

# Start vLLM server in background
echo "🚀 Starting vLLM server..."
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_NAME" \
    --served-model-name "$MODEL_NAME" \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --max-model-len "$MAX_MODEL_LEN" \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    --trust-remote-code \
    --dtype auto \
    --enforce-eager \
    &

VLLM_PID=$!

# Wait for vLLM to be ready
echo "⏳ Waiting for model server..."
MAX_WAIT=300
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$VLLM_PORT/v1/models > /dev/null 2>&1; then
        echo "✅ Model server ready!"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  Waiting... ($WAITED/${MAX_WAIT}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Model server failed to start within ${MAX_WAIT}s"
    kill $VLLM_PID 2>/dev/null
    exit 1
fi

# Run the agent
echo ""
echo "🏴 Starting Ozz agent..."
echo "=========================================="
python -m agent "$@"

# Cleanup
echo "🛑 Shutting down..."
kill $VLLM_PID 2>/dev/null
wait $VLLM_PID 2>/dev/null
echo "👋 Done."
