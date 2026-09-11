#!/usr/bin/env bash
# Writes Langfuse MCP Authorization headers as JSON for Claude Code headersHelper.
# Reads project-scoped keys from backend/.env (no secrets in repo MCP configs).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${LANGFUSE_ENV_FILE:-${ROOT}/backend/.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
	echo "langfuse-mcp-auth-headers: missing ${ENV_FILE}" >&2
	exit 1
fi

exec python3 - "${ENV_FILE}" <<'PY'
import base64
import json
import sys
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


env = load_env(Path(sys.argv[1]))
public = env.get("LANGFUSE_PUBLIC_KEY", "")
secret = env.get("LANGFUSE_SECRET_KEY", "")
if not public or not secret:
    print("langfuse-mcp-auth-headers: LANGFUSE_PUBLIC_KEY/SECRET_KEY unset", file=sys.stderr)
    sys.exit(1)

token = base64.b64encode(f"{public}:{secret}".encode()).decode("ascii")
print(json.dumps({"Authorization": f"Basic {token}"}))
PY
