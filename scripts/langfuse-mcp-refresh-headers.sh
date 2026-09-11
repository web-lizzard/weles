#!/usr/bin/env bash
# Write .cursor/langfuse-mcp.headers from backend/.env (no MCP process).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${LANGFUSE_ENV_FILE:-${ROOT}/backend/.env}"
HEADER_FILE="${ROOT}/.cursor/langfuse-mcp.headers"

if [[ ! -f "${ENV_FILE}" ]]; then
	echo "langfuse-mcp-refresh-headers: missing ${ENV_FILE}" >&2
	exit 1
fi

mkdir -p "${ROOT}/.cursor"
python3 - "${ENV_FILE}" "${HEADER_FILE}" <<'PY'
import base64
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


env_path = Path(sys.argv[1])
header_path = Path(sys.argv[2])
env = load_env(env_path)
public = env.get("LANGFUSE_PUBLIC_KEY", "")
secret = env.get("LANGFUSE_SECRET_KEY", "")
if not public or not secret:
    print("langfuse-mcp-refresh-headers: LANGFUSE_PUBLIC_KEY/SECRET_KEY unset", file=sys.stderr)
    sys.exit(1)

token = base64.b64encode(f"{public}:{secret}".encode()).decode("ascii")
header_path.write_text(f"Authorization: Basic {token}\n", encoding="utf-8")
PY

echo "Wrote ${HEADER_FILE}"
