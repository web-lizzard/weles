#!/usr/bin/env bash
# Emit export LANGFUSE_MCP_AUTH=... from backend/.env (for Cursor ${env:LANGFUSE_MCP_AUTH}).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/backend/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
	echo "sync-langfuse-mcp-auth: missing ${ENV_FILE}" >&2
	exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${LANGFUSE_PUBLIC_KEY:-}" || -z "${LANGFUSE_SECRET_KEY:-}" ]]; then
	echo "sync-langfuse-mcp-auth: LANGFUSE_PUBLIC_KEY/SECRET_KEY unset in ${ENV_FILE}" >&2
	exit 1
fi

AUTH="$(echo -n "${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}" | base64 -w 0)"
printf 'export LANGFUSE_MCP_AUTH=%q\n' "${AUTH}"
