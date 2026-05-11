FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p /app/config /app/data

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/config/config.yml
ENV DB_PATH=/app/data/instarss.db

RUN useradd --no-create-home --no-log-init --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "app.main"]
