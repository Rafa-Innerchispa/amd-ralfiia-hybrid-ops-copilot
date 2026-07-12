# Track 1 submission — 4 GB RAM / 2 vCPU / boot fast / 0-token local path
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/
COPY track1_agent/requirements.txt .

# Prebuilt CPU manylinux wheel (no gcc / no cmake)
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir httpx \
    && pip install --no-cache-dir llama-cpp-python==0.3.34 \
        --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# Bake Qwen2.5-0.5B Instruct Q4_K_M (~400MB) for offline 0-token NLP
RUN mkdir -p /app/models \
    && curl -L --fail --retry 3 \
        -o /app/models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
        "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf" \
    && chmod -R a+rX /app/models

COPY track1_agent/run_harness.py .

RUN mkdir -p /input /output \
    && chmod 777 /input /output \
    && chmod -R a+rX /app

ENV PYTHONPATH=/app \
    HARNESS_INPUT_PATH=/input/tasks.json \
    HARNESS_OUTPUT_PATH=/output/results.json \
    LOCAL_MODEL_PATH=/app/models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
    LOCAL_N_THREADS=2 \
    LOCAL_MAX_TOKENS=96 \
    ZERO_TOKEN_MODE=0

USER nobody

ENTRYPOINT ["python", "run_harness.py"]
