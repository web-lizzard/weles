#!/usr/bin/env bash
# Host-only: copy GITHUB_PACKAGES_TOKEN from workspace .env into devcontainer.env
# so docker run --env-file can inject it (devcontainer.json localEnv does not read .env).
set -euo pipefail

INIT_D_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${INIT_D_DIR}/../.." && pwd)"
OUT="${INIT_D_DIR}/../devcontainer.env"
SRC="${WORKSPACE_ROOT}/.env"

TOKEN=""
if [[ -f "${SRC}" ]]; then
	TOKEN="$(grep -E '^GITHUB_PACKAGES_TOKEN=' "${SRC}" | head -n1 | cut -d= -f2- | tr -d '\r"' || true)"
fi

if [[ -z "${TOKEN}" ]]; then
	echo "GITHUB_PACKAGES_TOKEN not found in ${SRC}; ordo install will be skipped in the container." >&2
	printf '# No GITHUB_PACKAGES_TOKEN — add it to %s and rebuild.\n' "${SRC}" >"${OUT}"
else
	printf 'GITHUB_PACKAGES_TOKEN=%s\n' "${TOKEN}" >"${OUT}"
	chmod 600 "${OUT}"
	echo "Synced GITHUB_PACKAGES_TOKEN into ${OUT}"
fi
