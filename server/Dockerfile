FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36 AS builder

ARG SOURCE_DATE_EPOCH=0
ENV SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    TZ=UTC \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_COMPILE=1

WORKDIR /build
COPY server/pyproject.toml /build/server/pyproject.toml
COPY server/app /build/server/app
COPY server/migrations /build/server/migrations
COPY server/migrate.py /build/server/migrate.py

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade 'pip==26.2.1' \
    && /opt/venv/bin/pip install 'setuptools==80.9.0' \
    && /opt/venv/bin/pip install --no-build-isolation /build/server \
    && find /opt/venv /build/server -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36 AS runtime

ARG SOURCE_DATE_EPOCH=0
ENV SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    TZ=UTC \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app/server
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/server/app /app/server/app
COPY --from=builder /build/server/migrations /app/server/migrations
COPY --from=builder /build/server/migrate.py /app/server/migrate.py

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["sh", "-c", "python migrate.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips='*'"]
