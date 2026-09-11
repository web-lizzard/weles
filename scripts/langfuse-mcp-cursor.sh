#!/usr/bin/env bash
# Cursor stdio MCP: proxy to Langfuse hosted HTTP with Basic auth from backend/.env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${LANGFUSE_ENV_FILE:-${ROOT}/backend/.env}"
HEADER_FILE="${ROOT}/.cursor/langfuse-mcp.headers"
MCP_URL="${LANGFUSE_MCP_URL:-https://cloud.langfuse.com/api/public/mcp}"

if [[ ! -f "${ENV_FILE}" ]]; then
	echo "langfuse-mcp-cursor: missing ${ENV_FILE}" >&2
	exit 1
fi

"${ROOT}/scripts/langfuse-mcp-refresh-headers.sh"

exec npx -y mcp-remote@0.13.5 "${MCP_URL}" --header-file "${HEADER_FILE}"
