# Multi-stage Dockerfile for Crypto TGE Monitor
# Optimized for production deployment

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_DIR="/app" \
    LOG_DIR="/var/log/crypto-tge-monitor" \
    STATE_DIR="/var/lib/crypto-tge-monitor"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser -d /app -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create directories
RUN mkdir -p $APP_DIR $LOG_DIR $STATE_DIR && \
    chown -R appuser:appuser $APP_DIR $LOG_DIR $STATE_DIR

# Copy application code
COPY --chown=appuser:appuser . $APP_DIR/

# Switch to non-root user
USER appuser
WORKDIR $APP_DIR

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python src/health_endpoint.py || exit 1

# Expose health check port
EXPOSE 8080

# Default command
CMD ["python", "src/main.py", "--mode", "continuous"]