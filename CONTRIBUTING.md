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

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
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

Run the full backend check suite locally — this mirrors what CI runs:

```bash
cd backend
ruff check .
ruff format --check .
pytest --cov=app
```

All three must pass. If `ruff format --check` fails, run `ruff format .` to
apply the fixes automatically.

## Code style

- Python code is formatted and linted with [Ruff](https://docs.astral.sh/ruff/);
  configuration lives in [`pyproject.toml`](pyproject.toml).
- Favor small, single-purpose functions and explicit types (`Mapped[...]`
  annotations, Pydantic schemas) over implicit behavior.
- Only add comments/docstrings where the *why* isn't obvious from the code —
  don't restate what the code already says.
- Database schema changes must ship with an Alembic migration
  (`alembic revision --autogenerate -m "..."`) and must not be edited after
  they've been merged to `main`.

## Tests

- New endpoints or business logic should come with unit tests under
  `backend/tests/unit/`, following the existing mock-based service/repository
  pattern in `backend/tests/conftest.py`.
- Test files must be named `test_*.py` so `pytest` can discover them.

## Reporting bugs / requesting features

Please open a GitHub issue with steps to reproduce (for bugs) or a clear
description of the use case (for features).

## Security issues

Do not open a public issue for security vulnerabilities — see
[SECURITY.md](SECURITY.md) instead.
