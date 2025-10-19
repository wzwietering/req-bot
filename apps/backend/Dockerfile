# Multi-stage Dockerfile for FastAPI backend with Poetry

# Build stage
FROM python:3.13.7-alpine3.22 AS builder

# Install system dependencies for building Python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Install Poetry
RUN pip install poetry==2.1.4

# Set Poetry configuration
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/opt/poetry_cache \
    POETRY_VIRTUALENVS_PATH=/opt/poetry_venvs

# Set working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install dependencies only (without the project itself)
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM python:3.13.7-alpine3.22 AS runtime

# Install runtime dependencies
RUN apk add --no-cache \
    sqlite \
    curl

# Create non-root user
RUN addgroup --system --gid 1001 appgroup
RUN adduser --system --uid 1001 --ingroup appgroup appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
ENV VIRTUAL_ENV=/app/.venv
COPY --from=builder /opt/poetry_venvs/specscribe-9TtSrW0h-py3.13 ${VIRTUAL_ENV}

# Make sure to use venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy application code
COPY . .

# Copy Alembic configuration
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Environment variables
ENV DATABASE_URL=sqlite:////app/data/specscribe.db
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start script
COPY --chown=appuser:appgroup <<EOF /app/start.sh
#!/bin/sh
set -e

# Activate virtual environment
export PATH="/app/.venv/bin:\$PATH"

# Run database migrations
echo "Running database migrations..."
/app/.venv/bin/python -m alembic upgrade head

# Start the application
echo "Starting FastAPI application..."
exec /app/.venv/bin/python specscribe/api_server.py --host 0.0.0.0 --port 8080
EOF

RUN chmod +x /app/start.sh

# Start the application
CMD ["/app/start.sh"]