FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY sentinel_core ./sentinel_core

USER 65532:65532
EXPOSE 8000

CMD ["uvicorn", "sentinel_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
