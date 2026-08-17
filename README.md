# Reverse ETL with AI Mapping

Open-source Reverse ETL tool for synchronizing data from PostgreSQL/ClickHouse to CRM systems (Bitrix24, AmoCRM) with AI-powered field mapping.

## Features (planned)
- 🔌 PostgreSQL and ClickHouse as sources
- 📊 Bitrix24 and AmoCRM as destinations
- 🤖 AI-assisted field mapping (local LLM via Ollama)
- ⏱ Scheduled syncs with incremental updates
- 🖥 Modern web interface

## Tech Stack
- Backend: Python 3.11+ + FastAPI + SQLAlchemy (async) + Alembic
- Frontend: React + TypeScript + Vite
- AI: Ollama (local)

## Project Structure
```
backend/    FastAPI application, CRUD API for sources, destinations, mappings and syncs
frontend/   React + TypeScript + Vite application
```

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill in SECRET_KEY / ENCRYPTION_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow.

## Status
🚧 Under active development

## License
[MIT](LICENSE)