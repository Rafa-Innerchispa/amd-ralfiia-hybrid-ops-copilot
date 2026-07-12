# Track 1 submission — 4 GB RAM / 2 vCPU / boot fast / 0-token local path
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

ENV HF_HOME=/app/hf_cache

COPY shared/ /app/shared/
COPY track1_agent/requirements.txt .

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt

# Pre-download and cache Qwen model weights
COPY track1_agent/download_model.py .
RUN python download_model.py && chmod -R 777 /app/hf_cache

COPY track1_agent/run_harness.py .
COPY track1_agent/agent_messages.json .

RUN mkdir -p /input /output \
    && chmod 777 /input /output \
    && chmod -R a+rX /app

ENV PYTHONPATH=/app \
    HARNESS_INPUT_PATH=/input/tasks.json \
    HARNESS_OUTPUT_PATH=/output/results.json \
    ZERO_TOKEN_MODE=0

USER nobody

ENTRYPOINT ["python", "run_harness.py"]
