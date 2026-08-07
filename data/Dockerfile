FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so the layer caches across code changes.
# The framework package is `services/` — `src/` never existed, so the old
# `COPY src/ ./src/` here failed the build outright.
COPY pyproject.toml .
COPY README.md .
COPY services/ ./services/
# `[dev]` brings pytest and httpx — this is the development image, and the
# suite is meant to be runnable inside it. Dockerfile.prod installs runtime
# dependencies only.
RUN pip install --no-cache-dir ".[dev]"

# Copy codebase
COPY . .

EXPOSE 8000

# Command names must match the craft CLI: `migrate fresh` (not migrate-fresh)
# and `db seed` (not db:seed). Running the test-suite on every boot was also
# dropped — a serve command should not depend on pytest.
CMD ["sh", "-c", "python dev.py migrate fresh --seed && python dev.py serve --host 0.0.0.0 --port 8000 --no-reload"]
