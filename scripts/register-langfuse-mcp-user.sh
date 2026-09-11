#!/usr/bin/env bash
# Merge Langfuse stdio MCP into ~/.cursor/mcp.json (User scope) so Customize lists it
# when project-scoped .cursor/mcp.json does not appear in the UI (Cursor 3.15–3.16, devcontainers).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_MCP="${HOME}/.cursor/mcp.json"
mkdir -p "${HOME}/.cursor"

python3 - "${USER_MCP}" "${ROOT}" <<'PY'
import json
import sys
from pathlib import Path

user_mcp = Path(sys.argv[1])
root = Path(sys.argv[2])

if user_mcp.exists():
    data = json.loads(user_mcp.read_text(encoding="utf-8"))
else:
    data = {}

servers = data.setdefault("mcpServers", {})
servers["langfuse"] = {
    "type": "stdio",
    "command": "bash",
    "args": [f"${{workspaceFolder}}/scripts/langfuse-mcp-cursor.sh"],
}

user_mcp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Registered langfuse MCP in {user_mcp}")
print("Reload Cursor window, then: Customize → MCPs (scope: User or this folder).")
PY
