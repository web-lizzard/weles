#!/usr/bin/env bash
# Installs @web-lizzard/ordo from GitHub Packages (GITHUB_PACKAGES_TOKEN via devcontainer.env).
set -euo pipefail

if command -v ordo >/dev/null 2>&1; then
	echo "Ordo already installed: $(ordo --version 2>/dev/null || echo 'version unknown')"
	exit 0
fi

if ! command -v node >/dev/null 2>&1; then
	echo "Node.js is not available; ensure the devcontainer Node feature is enabled." >&2
	exit 1
fi

node_major="$(node -p "process.versions.node.split('.')[0]")"
if [[ "${node_major}" -lt 20 ]]; then
	echo "Node.js >= 20 is required for Ordo (found $(node --version))." >&2
	exit 1
fi

TOKEN="${GITHUB_PACKAGES_TOKEN:-}"
if [[ -z "${TOKEN}" ]]; then
	echo "Warning: GITHUB_PACKAGES_TOKEN is not set; skipping @web-lizzard/ordo install." >&2
	echo "Add a classic GitHub PAT with read:packages to .env and rebuild the container." >&2
	exit 0
fi

ORDO_NPMRC="${HOME}/.config/ordo/npmrc"
mkdir -p "${HOME}/.local/bin" "$(dirname "${ORDO_NPMRC}")"
cat >"${ORDO_NPMRC}" <<EOF
@web-lizzard:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${TOKEN}
EOF
chmod 600 "${ORDO_NPMRC}"

echo "Installing @web-lizzard/ordo ..."
if ! NPM_CONFIG_PREFIX="${HOME}/.local" NPM_CONFIG_USERCONFIG="${ORDO_NPMRC}" npm install -g @web-lizzard/ordo; then
	echo "Warning: failed to install @web-lizzard/ordo; container will continue without it." >&2
	exit 0
fi

if ! command -v ordo >/dev/null 2>&1; then
	echo "Warning: ordo install finished but 'ordo' is not on PATH." >&2
	exit 0
fi

echo "Ordo installed: $(ordo --version 2>/dev/null || ordo version 2>/dev/null || echo 'version unknown')"
