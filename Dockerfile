# Ozz — HALctf Autonomous Pentesting Agent
# Docker image for DEF CON 34 AI Village HALctf
#
# Build:
#   docker build -t ozz:latest .
#
# Run:
#   docker run --gpus all -e TARGETS="10.0.0.1" ozz:latest

FROM nvidia/cuda:12.4.0-runtime-ubuntu24.04

LABEL maintainer="Ozz <halctf@ozz>"
LABEL description="Ozz — Autonomous Pentesting Agent for HALctf"
LABEL version="0.1.0"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    # Pentesting tools
    nmap \
    nikto \
    whatweb \
    gobuster \
    dirb \
    sqlmap \
    hydra \
    netcat-openbsd \
    curl \
    wget \
    git \
    # Utilities
    jq \
    net-tools \
    dnsutils \
    whois \
    file \
    strings \
    tmux \
    # Build deps for Python packages
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Remove EXTERNALLY-MANAGED marker
RUN rm -f /usr/lib/python3.*/EXTERNALLY-MANAGED

# Python dependencies (PyTorch, Transformers, FastAPI & Pentest libraries)
RUN pip3 install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cu124 \
    transformers \
    accelerate \
    fastapi \
    uvicorn \
    pydantic \
    requests \
    pwntools \
    beautifulsoup4 \
    lxml

# Create working directories
RUN mkdir -p /models /app /config /tmp/ozz /tmp/hf_cache

# Copy agent code and scripts
COPY agent/ /app/agent/
COPY scripts/ /app/scripts/
RUN chmod +x /app/entrypoint.sh /app/scripts/*.sh 2>/dev/null || true

# Copy wordlists (common ones)
RUN mkdir -p /usr/share/wordlists
RUN if [ -f /usr/share/wordlists/dirb/common.txt ]; then \
        echo "Wordlists already present"; \
    else \
        echo "Creating minimal wordlist"; \
        curl -sL "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" \
            -o /usr/share/wordlists/dirb/common.txt 2>/dev/null || \
        echo -e "admin\nlogin\nindex\nrobots.txt\n.git\n.svn\n.htaccess\nwp-admin\nwp-login\napi\nv1\nv2\ntest\ndev\nstaging\nconsole\ndashboard\nconfig\nbackup\ndb\ndatabase\nsql\nphpmyadmin\nserver-status\nserver-info" \
            > /usr/share/wordlists/dirb/common.txt; \
    fi

# Default configuration
ENV MODEL_PATH=/models
ENV MODEL_NAME="Qwen/Qwen2.5-Coder-3B-Instruct"
ENV HF_HOME="/tmp/hf_cache"
ENV VLLM_PORT=8000
ENV GPU_MEMORY_UTILIZATION=0.85
ENV MAX_MODEL_LEN=8192
ENV TENSOR_PARALLEL_SIZE=1
ENV MAX_TOKENS=4096
ENV TEMPERATURE=0.3
ENV TARGETS=""

WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/v1/models || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
