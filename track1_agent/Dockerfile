# Track 1 submission image — AMD automated evaluator (4 GB RAM, 2 vCPU, boot <60s)
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

COPY shared/ /app/shared/
COPY track1_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY track1_agent/run_harness.py .

RUN mkdir -p /input /output && chmod 777 /input /output

ENV HARNESS_INPUT_PATH=/input/tasks.json \
    HARNESS_OUTPUT_PATH=/output/results.json

ENTRYPOINT ["python", "run_harness.py"]
