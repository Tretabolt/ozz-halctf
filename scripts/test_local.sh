#!/bin/bash
# Ozz — Local test with a simple vulnerable target
# Uses a known vulnerable Docker image for testing

set -e

echo "🏴 Ozz Local Test"
echo "================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Check for GPU
if ! nvidia-smi &> /dev/null; then
    echo "⚠️  nvidia-smi not found. The agent needs a GPU for the LLM."
    echo "   You can still test the tools by running: docker run -it ozz:latest shell 'nmap --version'"
    exit 1
fi

echo "📦 Starting vulnerable test target..."
# Start a simple vulnerable web server for testing
docker run -d --name ozz-test-target \
    -p 8080:80 \
    vulnerables/web-dvwa 2>/dev/null || \
    docker run -d --name ozz-test-target \
    -p 8080:80 \
    citizenstig/dvwa 2>/dev/null || \
    echo "Could not start DVWA, using basic nginx instead" && \
    docker run -d --name ozz-test-target -p 8080:80 nginx

echo "🎯 Test target available at: http://localhost:8080"
echo ""

echo "🏴 Starting Ozz agent against local target..."
echo "   This will use the model server and test against localhost:8080"
echo ""

# Run Ozz against the test target
docker run --gpus all \
    --network host \
    -e TARGETS="127.0.0.1" \
    -e MODEL_NAME="Qwen/Qwen2.5-Coder-7B-Instruct" \
    -v ./models:/models \
    ozz:latest

# Cleanup
echo ""
echo "🧹 Cleaning up test target..."
docker stop ozz-test-target 2>/dev/null
docker rm ozz-test-target 2>/dev/null

echo "✅ Test complete!"
