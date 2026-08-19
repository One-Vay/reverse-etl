# Contributing

Thanks for your interest in contributing to Reverse ETL! This document explains
how to set up the project locally, the workflow we use, and the standards your
change is expected to meet.

## Project layout

```
backend/    FastAPI application (Python 3.11+)
frontend/   React + TypeScript + Vite application
```

## Getting started (backend)

1. Create and activate a virtual environment:

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Install dependencies. `requirements-dev.txt` pulls in `requirements.txt`
   plus test tooling (pytest, ruff, testcontainers) — use it for local dev.
   The Docker image installs only `requirements.txt` (runtime deps):

   ```bash
   pip install -r requirements-dev.txt
   ```

3. Copy the environment template and fill in real values:

   ```bash
   cp .env.example .env
   ```

4. Run database migrations:

   ```bash
   alembic upgrade head
   ```

5. Start the development server:

   ```bash
   uvicorn app.main:app --reload
   ```

## Getting started (full stack, Docker Compose)

`docker compose up -d --build` starts `db`, `backend`, and `frontend`. The
optional local-LLM service (`ollama`, used for AI mapping suggestions) is
gated behind a Compose profile and is **not** started by the plain command
above — opt in explicitly:

```bash
docker compose --profile llm up -d
```

Then enable "AI mapping suggestions" in the console's Settings page.

### Database migrations against the Docker stack

If you're running via Docker Compose, don't run Alembic against
`localhost:5432` from the host — on a machine that also has a native
Postgres install, both can end up listening on the same port and Windows/OS
port-forwarding may route your connection to the wrong database. Run Alembic
*inside* the Docker network instead:

```bash
# Generate a migration (note: --name, not --rm, so the container survives
# long enough to copy the generated file out):
docker compose run --name migration-gen --entrypoint alembic backend \
  revision --autogenerate -m "describe the change"
docker cp migration-gen:/app/alembic/versions/<generated_file>.py backend/alembic/versions/
docker rm migration-gen

# Review the generated migration (autogenerate doesn't always get NOT NULL
# defaults on existing rows right — add server_default= where needed), then
# rebuild the image so it's included, and apply:
docker compose build backend
docker compose run --rm --entrypoint alembic backend upgrade head
```

## Workflow

We follow [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow):

1. Branch off `main` using a `<type>/<short-description>` name, e.g.
   `feature/add-login`, `fix/login-error`, `docs/readme-update`,
   `chore/update-deps`, `refactor/auth-service`.
2. Commit small, focused changes with clear messages.
3. Push your branch and open a Pull Request against `main`.
4. Make sure CI is green and address review feedback.
5. Squash/merge once approved; delete the branch afterwards.

## Before opening a Pull Request

Run the full check suite locally — this mirrors every job in
[`.github/workflows/test.yml`](.github/workflows/test.yml). A change that
only passes some of these will fail CI:

```bash
cd backend
ruff check .
ruff format --check .
mypy app
pytest --cov=app
pytest tests/integration -m integration -v   # requires Docker
```

```bash
cd frontend
npm run lint
npm run typecheck
npm run format:check
npm run test
npm run build
```

If `ruff format --check` or `npm run format:check` fails, run `ruff format .`
/ `npm run format` to apply the fixes automatically.

There used to be a second, separate CI workflow (`ci.yml`) that duplicated
`test.yml` with a different, half-configured job set (no `mypy` config, no
`Vitest` setup) — it failed on every push silently enough that it was easy
to miss. It's been folded into the single workflow above; don't recreate a
second one.

## Code style

- Python code is formatted and linted with [Ruff](https://docs.astral.sh/ruff/)
  and type-checked with [mypy](https://mypy.readthedocs.io/); configuration
  for both lives in [`pyproject.toml`](pyproject.toml).
- Favor small, single-purpose functions and explicit types (`Mapped[...]`
  annotations, Pydantic schemas) over implicit behavior.
- Only add comments/docstrings where the *why* isn't obvious from the code —
  don't restate what the code already says.
- Database schema changes must ship with an Alembic migration
  (`alembic revision --autogenerate -m "..."`) and must not be edited after
  they've been merged to `main`.
- A Pydantic model's fields must match what code actually sets on it —
  passing an unrecognized keyword argument doesn't raise (Pydantic v2
  defaults to `extra="ignore"`), it's silently dropped. This bit us once
  (`SyncUpdate(next_run=...)` never persisted); `mypy`'s `call-arg` check is
  what would have caught it, which is why it's part of CI.

## Tests

- New endpoints or business logic should come with unit tests under
  `backend/tests/unit/`, following the existing mock-based service/repository
  pattern in `backend/tests/conftest.py`.
- Test files must be named `test_*.py` so `pytest` can discover them.
- Connectors (`backend/app/connectors/`) get two layers of tests:
  - **Unit tests** (`backend/tests/unit/connectors/`) mock the driver
    (e.g. `asyncpg`) entirely — no Docker needed, run as part of `pytest`.
  - **Integration tests** (`backend/tests/integration/`) spin up the real
    system via [testcontainers](https://testcontainers-python.readthedocs.io/)
    and are marked `@pytest.mark.integration`, which excludes them from the
    default `pytest` run (see `addopts` in `pyproject.toml`). They require
    Docker; run them explicitly before merging any connector change:

    ```bash
    pytest tests/integration -m integration -v
    ```

## Reporting bugs / requesting features

Please open a GitHub issue with steps to reproduce (for bugs) or a clear
description of the use case (for features).

## Security issues

Do not open a public issue for security vulnerabilities — see
[SECURITY.md](SECURITY.md) instead.
