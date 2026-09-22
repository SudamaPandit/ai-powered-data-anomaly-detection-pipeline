FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system pipeline && adduser --system --ingroup pipeline pipeline

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY config ./config

USER pipeline

ENTRYPOINT ["python", "-m", "anomaly_pipeline"]
CMD ["--help"]

