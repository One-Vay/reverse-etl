# Reverse ETL with AI Mapping

Self-hosted Reverse ETL tool for syncing data from PostgreSQL/ClickHouse to CRM
systems (Bitrix24, AmoCRM), with AI-assisted field mapping and everything
configurable from a web console — no code, no config files, no redeploys.

## Features

- 🔌 **Sources**: PostgreSQL, ClickHouse
- 📊 **Destinations**: Bitrix24, AmoCRM — with an interactive drag-and-drop
  field-mapping board
- 🤖 **AI-assisted field mapping** via an optional local LLM (Ollama) — never
  leaves your network
- ⏱ **Scheduler** with an hours/days interval picker (no cron expressions) and
  optional incremental syncs. Survives restarts: a run that was due while the
  container was down still fires on the next poll, phase-aligned to the
  original schedule rather than bursting through every missed occurrence.
- 📬 **Telegram notifications** — a report after every scheduled run
  (success/failure, record counts), flagged when it ran late
- 📅 **Upcoming-runs calendar** on the dashboard — every active pipeline's
  next 7 days of scheduled fires at a glance
- 🖥 **Fully web-configurable** — connections, mappings, schedules, the
  scheduler itself, and the AI/Telegram integrations are all managed from the
  UI; nothing requires editing `.env` or redeploying

## Tech Stack
- Backend: Python 3.12+ · FastAPI · SQLAlchemy (async) · Alembic
- Frontend: React · TypeScript · Vite
- AI: Ollama (local, optional)

## Project Structure
```
backend/    FastAPI application — connectors, scheduler, mapping/AI suggestion engine, settings
frontend/   React + TypeScript + Vite console
```

## Getting Started (Docker Compose)

The fastest way to run the full stack:

```bash
cp .env.example .env   # fill in SECRET_KEY / ENCRYPTION_KEY, see the file for how
docker compose up -d --build
```

- Web console: `http://localhost` (or `$FRONTEND_PORT`)
- API + docs: `http://localhost:8000/docs` (or `$BACKEND_PORT`)

Database migrations run automatically on backend startup.

### Optional: local AI mapping suggestions

The Ollama service isn't started by default — opt in explicitly:

```bash
docker compose --profile llm up -d
```

Then in the console's **Settings** page, enable "AI mapping suggestions"
(base URL `http://ollama:11434` is the default inside the compose network)
and pick a model — it's pulled automatically the first time it's needed.

### Optional: Telegram notifications

In **Settings → Telegram notifications**, enable the switch and paste a bot
token (from [@BotFather](https://t.me/BotFather)) and your chat ID. Use "Send
test message" to verify before relying on it — every scheduled pipeline run
will then report its outcome to that chat, including a delay warning if it
ran late (e.g. after a container restart caused a missed run to catch up).

## Getting Started (backend only, without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill in SECRET_KEY / ENCRYPTION_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

### Running tests

```bash
cd backend
pytest --cov=app
```

### Linting

```bash
cd backend
ruff check .
ruff format --check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow,
including the Docker-based Alembic migration workflow and frontend checks.

## Status
🚧 Under active development

## License
[MIT](LICENSE)
