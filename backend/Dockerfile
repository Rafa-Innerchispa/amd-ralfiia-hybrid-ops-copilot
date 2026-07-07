FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY backend/app /app/app
COPY scripts/seed_mongo.py /app/scripts/seed_mongo.py
ENV PYTHONPATH=/app
EXPOSE 8220
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8220"]
