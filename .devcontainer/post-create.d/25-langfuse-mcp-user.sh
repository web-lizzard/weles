#!/usr/bin/env bash
# User-scope MCP entry so Customize lists langfuse in devcontainers (project UI often empty).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "${ROOT}/scripts/register-langfuse-mcp-user.sh"
