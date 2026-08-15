# Pulse Monitor - Multi-stage Dockerfile for ARM64 (Raspberry Pi)

# Build stage
FROM python:3.13-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install project
COPY . .
RUN pip install --no-cache-dir --user -e ".[dev]"

# Runtime stage
FROM python:3.13-slim-bookworm

LABEL maintainer="thejedi433"
LABEL description="Pulse - A minimal service uptime monitor"

# Create non-root user
RUN useradd --create-home --shell /bin/bash pulse

# Create directories for config and data
RUN mkdir -p /config /data && chown -R pulse:pulse /config /data

WORKDIR /home/pulse

# Copy installed package from builder
COPY --from=builder --chown=pulse:pulse /root/.local /home/pulse/.local

# Add to PATH
ENV PATH="/home/pulse/.local/bin:$PATH"

# Switch to non-root user
USER pulse

# Default volume mounts
VOLUME ["/config", "/data"]

# Health check (checks if pulse CLI works)
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
    CMD pulse --version || exit 1

# Default command: run monitor daemon
CMD ["pulse", "monitor"]
