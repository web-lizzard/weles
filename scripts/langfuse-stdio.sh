#!/bin/bash
set -e

if [ -f "${BASH_SOURCE%/*}/../../.env" ]; then
  set -a
  source "${BASH_SOURCE%/*}/../../.env"
  set +a
fi

export AUTH_HEADER="Basic ${LANGFUSE_MCP_TOKEN}"

exec npx -y mcp-remote https://cloud.langfuse.com/api/public/mcp \
  --header "Authorization:${AUTH_HEADER}"