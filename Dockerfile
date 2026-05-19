FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG CACHE_BUST=1
COPY . .

EXPOSE 8080

CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
