#!/usr/bin/env bash
# Activate pnpm via corepack (Node 22 ships corepack; no separate install step).
set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
	echo "Node.js is not available; ensure the devcontainer Node feature is enabled." >&2
	exit 1
fi

corepack enable
corepack prepare pnpm@11.24.0 --activate

echo "pnpm activated: $(pnpm --version)"
