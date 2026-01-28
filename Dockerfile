# syntax=docker/dockerfile:1.7
# Multi-stage optimized Dockerfile for Code Review API
# Stage 1: Builder - prepare dependencies
FROM python:3.13-slim AS builder

WORKDIR /build

ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy only dependency files for better caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without dev dependencies for production)
RUN poetry install --no-interaction --no-ansi --no-root --no-dev


# Stage 2: Runtime - minimal production image
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 -s /sbin/nologin appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /build/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Use tini to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
