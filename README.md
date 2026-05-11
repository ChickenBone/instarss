# instarss

Polls RSS/Atom feeds on a cron schedule and saves new items to your [Instapaper](https://www.instapaper.com) account. Runs as a Docker container, configured via a single YAML file.

## Features

- Supports any RSS or Atom feed
- Configurable cron schedule (per-instance, in `config.yml`)
- Deduplicates via SQLite — never submits the same item twice
- Backfill guard — ignores items older than a configurable number of days
- Per-feed error isolation — one broken feed never stops the others
- Automatic retry with exponential backoff on Instapaper API errors
- Graceful shutdown on `SIGTERM` (Docker-safe)
- Published to GHCR via GitHub Actions; multi-arch (`amd64` + `arm64`)

## Quick Start

### 1. Create the working directories

```bash
mkdir -p config data
```

### 2. Scaffold the config

Run once to generate `config/config.yml`:

```bash
docker run --rm \
  -v "$(pwd)/config:/app/config" \
  ghcr.io/<your-username>/instarss:latest
```

The container exits and writes a template to `config/config.yml`.

### 3. Edit the config

```yaml
instapaper:
  username: "your@email.com"
  password: "yourpassword"

schedule: "*/30 * * * *"  # every 30 minutes

feeds:
  - name: "Hacker News Best"
    url: "https://hnrss.org/best"
    enabled: true
  - name: "My Blog"
    url: "https://example.com/feed.xml"
    enabled: true

settings:
  max_items_per_run: 20  # max new items submitted per feed per run
  backfill_days: 7       # ignore items older than this (0 = no limit)
  request_timeout: 30
  log_level: "INFO"
```

### 4. Run with Docker Compose

Set your GitHub username and start the service:

```bash
export GITHUB_USER=your-username
docker compose up -d
```

The service runs in the background with `restart: unless-stopped`. Logs:

```bash
docker compose logs -f
```

## Configuration Reference

| Key | Default | Description |
|-----|---------|-------------|
| `instapaper.username` | — | Your Instapaper account email |
| `instapaper.password` | — | Your Instapaper password (use any value if your account has none) |
| `schedule` | `*/30 * * * *` | Standard 5-field cron expression |
| `feeds[].name` | — | Display name (used in logs) |
| `feeds[].url` | — | RSS or Atom feed URL |
| `feeds[].enabled` | `true` | Set to `false` to skip a feed without removing it |
| `settings.max_items_per_run` | `20` | Cap on new submissions per feed per run |
| `settings.backfill_days` | `7` | Items older than this are marked seen but not submitted |
| `settings.request_timeout` | `30` | HTTP timeout in seconds (feeds + Instapaper API) |
| `settings.log_level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

### Environment Variable Overrides

| Variable | Description |
|----------|-------------|
| `CONFIG_PATH` | Path to `config.yml` inside the container (default: `/app/config/config.yml`) |
| `DB_PATH` | Path to the SQLite database (default: `/app/data/instarss.db`) |
| `LOG_LEVEL` | Overrides `settings.log_level`; takes effect if more verbose than config value |

## Building Locally

```bash
docker build -t instarss-local .

# Run with local image
docker run --rm \
  -v "$(pwd)/config:/app/config" \
  -v "$(pwd)/data:/app/data" \
  instarss-local
```

Or swap the image in `docker-compose.yml`:

```yaml
services:
  instarss:
    build: .   # replace the image: line with this
```

## Publishing to GHCR

Push to `main` or tag a release — GitHub Actions handles the rest:

```bash
git push origin main           # builds and pushes :latest + :sha-<hash>
git tag v1.0.0 && git push --tags  # also pushes :v1.0.0
```

The workflow (`.github/workflows/docker-publish.yml`) runs tests first and only pushes on success. No extra secrets are needed; it uses `GITHUB_TOKEN`.

## Data Persistence

| Path (container) | Host mount | Contents |
|-----------------|------------|----------|
| `/app/config/config.yml` | `./config/config.yml` | Your configuration |
| `/app/data/instarss.db` | `./data/instarss.db` | SQLite state (processed item GUIDs) |

To reset state and reprocess all feeds, delete `data/instarss.db`.

## Running Tests

```bash
pip install -r requirements.txt pytest pytest-mock responses
pytest tests/ -v
```
