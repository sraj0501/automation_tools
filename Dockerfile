# syntax=docker/dockerfile:1.6
# Multi-stage Dockerfile for DevTrack
# Stage 1: Build Go application
FROM golang:1.24-alpine AS go-builder

# Install build dependencies (build-base provides gcc, musl, make)
RUN apk add --no-cache git build-base

WORKDIR /build

# Copy Go module files
COPY devtrack/go.mod devtrack/go.sum ./
RUN go mod download

# Copy Go source code
COPY devtrack/ ./

# Build the binary
RUN CGO_ENABLED=1 go build -ldflags="-w -s" -o devtrack-cli .

# Stage 2: Base Python environment with cached apt/uv layers
FROM python:3.11-slim AS python-base

ENV PATH="/root/.local/bin:${PATH}"

RUN --mount=type=cache,target=/var/lib/apt \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        sqlite3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Stage 3: Install Python dependencies once
FROM python-base AS python-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache-dir \
        spacy \
        en-core-web-sm==3.7.1 \
        dateparser \
        sentence-transformers \
        scikit-learn \
        fuzzywuzzy \
        python-Levenshtein \
        ollama

# Stage 4: Runtime environment
FROM python-base AS runtime

# Copy Python deps from cached stage
COPY --from=python-deps /usr/local /usr/local

# Create app user
RUN useradd -m -u 1000 devtrack && \
    mkdir -p /home/devtrack/.local/share/devtrack && \
    mkdir -p /home/devtrack/.config/devtrack

# Set working directory
WORKDIR /app

# Copy built binary from builder stage
COPY --from=go-builder /build/devtrack-cli /usr/local/bin/devtrack-cli
RUN chmod +x /usr/local/bin/devtrack-cli

# Copy Python backend and entrypoints
COPY backend/ /app/backend/
COPY main.py python_bridge.py /app/
COPY pyproject.toml /app/

# Set up environment
ENV PATH="/home/devtrack/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV DEVTRACK_DATA_DIR=/home/devtrack/.local/share/devtrack
ENV DEVTRACK_CONFIG_DIR=/home/devtrack/.config/devtrack

# Change ownership to app user
RUN chown -R devtrack:devtrack /app /home/devtrack

# Switch to non-root user
USER devtrack

# Volumes for persistent data
VOLUME ["/home/devtrack/.local/share/devtrack", "/home/devtrack/.config/devtrack", "/workspace"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD devtrack-cli --version || exit 1

# Default command
ENTRYPOINT ["/usr/local/bin/devtrack-cli"]
CMD ["--help"]
