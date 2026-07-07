FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY agent_smart_quoter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY agent_smart_quoter/app /app/app
ENV PYTHONPATH=/app
EXPOSE 8221
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8221"]
