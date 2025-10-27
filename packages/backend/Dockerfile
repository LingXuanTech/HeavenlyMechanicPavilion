# Multi-stage Dockerfile for TradingAgents Backend
# Stage 1: Base image with uv
FROM python:3.13-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Stage 2: Dependencies
FROM base AS dependencies

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Install dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt

# Stage 3: Build
FROM dependencies AS builder

# Copy source code
COPY . .

# Install the package
RUN uv pip install --system --no-cache -e .

# Stage 4: Production
FROM python:3.13-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 tradingagents && \
    mkdir -p /app /app/results /app/data && \
    chown -R tradingagents:tradingagents /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy application code
COPY --chown=tradingagents:tradingagents . .

# Copy alembic configuration
COPY --chown=tradingagents:tradingagents alembic.ini ./
COPY --chown=tradingagents:tradingagents alembic ./alembic

USER tradingagents

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/tradingagents/.local/bin:$PATH" \
    TRADINGAGENTS_RESULTS_DIR=/app/results

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
