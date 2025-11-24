#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "Multiagent Firewall - Integration Tests Runner"
echo "=================================================="
echo ""

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "ERROR: .env file not found in integration_tests directory!"
  echo ""
  echo "Please create a .env file with your LLM configuration:"
  echo "  cd $SCRIPT_DIR"
  echo "  cp .env.example .env"
  echo "  # Edit .env and add your API key"
  echo ""
  exit 1
fi

echo "Loading environment variables from .env..."
export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)

if [ -z "$LLM_API_KEY" ]; then
  echo "WARNING: LLM_API_KEY is not set in .env file"
  echo "Tests will be skipped!"
  echo ""
fi

echo "Configuration:"
echo "  LLM_PROVIDER: ${LLM_PROVIDER:-not set}"
echo "  LLM_MODEL: ${LLM_MODEL:-not set}"
echo "  LLM_API_KEY: ${LLM_API_KEY:+***hidden***}"
echo ""

cd "$PROJECT_ROOT"

echo "Syncing test dependencies with uv..."
uv sync --group test

echo "Clearing cached test results..."
rm -f "$SCRIPT_DIR/.test_results_cache.json"

echo "Running integration tests..."
echo ""
uv run pytest integration_tests/ -v -m integration -s

echo ""
echo "=================================================="
echo "Integration tests completed!"
echo "=================================================="
