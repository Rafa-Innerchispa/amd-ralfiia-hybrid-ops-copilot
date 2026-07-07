FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY agent_watchdog/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY agent_watchdog/app /app/app
ENV PYTHONPATH=/app
EXPOSE 8222
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8222"]
