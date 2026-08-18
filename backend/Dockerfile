# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

# Install dependencies first so this layer is cached unless requirements.txt changes.
# Every pinned dependency ships a prebuilt manylinux wheel for this platform,
# so no compiler / apt packages are needed here.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .
RUN chmod +x entrypoint.sh

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
