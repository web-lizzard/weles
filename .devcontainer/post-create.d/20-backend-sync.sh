#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${WORKSPACE_ROOT}/backend/src:${PYTHONPATH:-}"
cd "${WORKSPACE_ROOT}/backend"

uv sync

echo "Backend dependencies synced."
