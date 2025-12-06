# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./ 

RUN pip install --no-cache-dir fastapi==0.119.0 uvicorn==0.37.0 sqlalchemy==2.0.44 psycopg2-binary==2.9.11 pydantic==2.12.2 qrcode==8.2 pillow==12.0.0 python-dotenv==1.1.1

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
