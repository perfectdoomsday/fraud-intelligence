FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-core.txt /app/backend/requirements-core.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-core.txt
COPY backend /app/backend
COPY ml /app/ml
COPY scripts /app/scripts
RUN mkdir -p /app/artifacts /app/data
EXPOSE 8000
CMD ["sh", "-c", "python scripts/bootstrap_model.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
