#!/bin/bash
# Download and prepare the model for Ozz
# Run this before building the Docker image if you want to bake the model in

set -e

MODEL_NAME="${1:-Qwen/Qwen2.5-Coder-7B-Instruct}"
MODEL_DIR="${2:-./models}"

echo "🏴 Ozz Model Downloader"
echo "======================="
echo "Model: $MODEL_NAME"
echo "Destination: $MODEL_DIR"
echo ""

# Install huggingface-hub if needed
pip install -q huggingface-hub 2>/dev/null || true

# Download model
echo "📥 Downloading model..."
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='$MODEL_NAME',
    local_dir='$MODEL_DIR/$(basename $MODEL_NAME)',
    local_dir_use_symlinks=False,
)
print('✅ Model downloaded!')
"

echo ""
echo "✅ Model ready at: $MODEL_DIR/$(basename $MODEL_NAME)"
echo ""
echo "To build with the model baked in:"
echo "  docker build --build-arg MODEL_DIR=$MODEL_DIR -t ozz:latest ."
echo ""
echo "Or mount at runtime:"
echo "  docker run --gpus all -v $MODEL_DIR:/models -e TARGETS=x ozz:latest"
