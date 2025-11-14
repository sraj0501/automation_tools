# Multi-stage Dockerfile for DevTrack
# Stage 1: Build Go application
FROM golang:1.24-alpine AS go-builder

# Install build dependencies
RUN apk add --no-cache git

WORKDIR /build

# Copy Go module files
COPY devtrack/go.mod devtrack/go.sum ./
RUN go mod download

# Copy Go source code
COPY devtrack/ ./

# Build the binary
RUN CGO_ENABLED=1 go build -ldflags="-w -s" -o devtrack-cli .

# Stage 2: Runtime environment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 devtrack && \
    mkdir -p /home/devtrack/.local/share/devtrack && \
    mkdir -p /home/devtrack/.config/devtrack

# Set working directory
WORKDIR /app

# Copy built binary from builder stage
COPY --from=go-builder /build/devtrack-cli /usr/local/bin/devtrack-cli
RUN chmod +x /usr/local/bin/devtrack-cli

# Copy Python backend
COPY backend/ /app/backend/
COPY main.py python_bridge.py /app/
COPY pyproject.toml /app/

# Install Python dependencies
RUN pip install --no-cache-dir --user \
    spacy \
    dateparser \
    sentence-transformers \
    scikit-learn \
    fuzzywuzzy \
    python-Levenshtein \
    ollama

# Download spaCy model
RUN python3 -m spacy download en_core_web_sm

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
