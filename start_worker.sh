#!/usr/bin/env bash
# Start Dramatiq worker for background document processing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source venv/bin/activate

echo "Starting Dramatiq worker for llm_gateway..."
exec dramatiq workers.worker_entrypoint
