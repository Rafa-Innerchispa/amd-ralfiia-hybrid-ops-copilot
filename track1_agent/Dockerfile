# Track 1 submission — 4 GB RAM / 2 vCPU / boot fast / 0-token local path
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

COPY shared/ /app/shared/
COPY track1_agent/requirements.txt .

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt

COPY track1_agent/run_harness.py .
COPY track1_agent/agent_messages.json .

RUN mkdir -p /input /output \
    && chmod 777 /input /output \
    && chmod -R a+rX /app

ENV PYTHONPATH=/app \
    HARNESS_INPUT_PATH=/input/tasks.json \
    HARNESS_OUTPUT_PATH=/output/results.json \
    ZERO_TOKEN_MODE=0

ENTRYPOINT ["python", "run_harness.py"]
