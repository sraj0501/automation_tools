#!/bin/bash

# DevTrack Docker Wrapper
# Makes DevTrack container callable like a native CLI application

set -e

# Configuration
DOCKER_IMAGE="devtrack:latest"
CONTAINER_NAME="devtrack-app"
WORKSPACE_PATH="${WORKSPACE_PATH:-$HOME/workspace}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Desktop." >&2
    exit 1
fi

# Check if docker-compose services are running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Check if image exists
    if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
        echo "Error: DevTrack image not found. Please run the installer first." >&2
        exit 1
    fi
    
    # Start services if they're not running
    SCRIPT_DIR="$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")"
    REPO_DIR="$(dirname "$SCRIPT_DIR")"
    
    if [ -f "$REPO_DIR/docker-compose.yml" ]; then
        cd "$REPO_DIR"
        docker-compose up -d >/dev/null 2>&1
    else
        echo "Error: docker-compose.yml not found. DevTrack may not be properly installed." >&2
        exit 1
    fi
fi

# Get current directory relative to workspace
CURRENT_DIR="$(pwd)"
REL_PATH="${CURRENT_DIR#$WORKSPACE_PATH}"
if [ "$REL_PATH" = "$CURRENT_DIR" ]; then
    # Not inside workspace, use workspace root
    WORKDIR="/workspace"
else
    # Inside workspace, maintain relative path
    WORKDIR="/workspace${REL_PATH}"
fi

# Run devtrack command in container
docker exec -it \
    -w "$WORKDIR" \
    -e TERM="$TERM" \
    -e COLORTERM="$COLORTERM" \
    "$CONTAINER_NAME" \
    devtrack-cli "$@"
