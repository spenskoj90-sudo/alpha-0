FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY server/pyproject.toml /build/server/pyproject.toml
COPY server/app /build/server/app
COPY server/migrations /build/server/migrations
COPY server/migrate.py /build/server/migrate.py

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install /build/server

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN addgroup --system sentinel && adduser --system --ingroup sentinel sentinel
WORKDIR /app/server
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/server/app /app/server/app
COPY --from=builder /build/server/migrations /app/server/migrations
COPY --from=builder /build/server/migrate.py /app/server/migrate.py

USER sentinel
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["sh", "-c", "python migrate.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips='*'"]
