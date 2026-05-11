FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create user at build time — entrypoint remaps UID/GID at runtime via usermod/groupmod
RUN groupadd -g 1000 appuser \
    && useradd -u 1000 -g 1000 --no-create-home appuser \
    && mkdir -p /app/config /app/data

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/config/config.yml
ENV DB_PATH=/app/data/instarss.db
ENV PUID=1000
ENV PGID=1000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "app.main"]
