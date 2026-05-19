FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s CMD curl -f http://localhost:${PORT:-8080}/ || exit 1

CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
