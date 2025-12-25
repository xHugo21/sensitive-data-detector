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
  echo ""
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: ./run_integration_tests.sh test_cases.yaml"
  exit 1
fi

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  echo "Usage: ./run_integration_tests.sh test_cases.yaml"
  exit 0
fi

CASES_FILE="$1"

if [[ "$CASES_FILE" = /* ]]; then
  CASES_PATH="$CASES_FILE"
else
  CASES_PATH="$SCRIPT_DIR/$CASES_FILE"
fi

if [ ! -f "$CASES_PATH" ]; then
  echo "ERROR: test cases file not found: $CASES_PATH"
  exit 1
fi

echo "Loading environment variables from .env..."
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    ""|\#*) continue ;;
  esac

  key="${line%%=*}"
  value="${line#*=}"

  key="${key#"${key%%[![:space:]]*}"}"
  key="${key%"${key##*[![:space:]]}"}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"

  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:-1}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:-1}"
  fi

  export "$key=$value"
done < "$SCRIPT_DIR/.env"
export INTEGRATION_TESTS_FILE="$CASES_PATH"

if [ -z "$LLM_API_KEY" ]; then
  echo "WARNING: LLM_API_KEY is not set in .env file"
  echo "Tests will be skipped!"
  echo ""
fi

echo "Configuration:"
echo "  LLM_PROVIDER: ${LLM_PROVIDER:-not set}"
echo "  LLM_MODEL: ${LLM_MODEL:-not set}"
echo "  TEST_CASES_FILE: $CASES_PATH"
echo ""

cd "$PROJECT_ROOT"

echo "Syncing test dependencies with uv..."
uv sync --extra ner --extra file-analysis --group test

echo "Running integration tests..."
echo ""
uv run pytest integration_tests/test_end_to_end_detection.py -v -m integration -s
