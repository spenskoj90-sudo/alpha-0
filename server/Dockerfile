FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system sentinel && adduser --system --ingroup sentinel sentinel

COPY server/pyproject.toml /app/server/pyproject.toml
COPY server/app /app/server/app
COPY server/migrations /app/server/migrations
COPY server/migrate.py /app/server/migrate.py

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir '/app/server[test]'

USER sentinel
WORKDIR /app/server

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["sh", "-c", "python migrate.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
