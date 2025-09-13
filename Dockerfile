# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PCS_ARGS="--auto --interval 30"

WORKDIR /app

# Install dependencies first for better build caching
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY pcs_pushover ./pcs_pushover

# Default command: auto-discover races and poll
CMD ["/bin/sh", "-c", "python -m pcs_pushover.cli ${PCS_ARGS}"]

