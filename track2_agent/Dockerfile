# Track 2 submission image — AMD automated evaluator (4 GB RAM, ffmpeg for frames)
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/
COPY track2_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY track2_agent/run_vision.py .

ENV PYTHONPATH=/app

RUN mkdir -p /input /output

ENV HARNESS_INPUT_PATH=/input/tasks.json \
    HARNESS_OUTPUT_PATH=/output/results.json

ENTRYPOINT ["python", "run_vision.py"]
