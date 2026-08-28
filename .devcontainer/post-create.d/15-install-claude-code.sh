#!/usr/bin/env bash
# Installs Claude Code CLI and verifies credentials bind-mount from host ~/.claude-personal.
set -euo pipefail

CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-/home/vscode/.claude-personal}"

if [[ ! -d "${CLAUDE_CONFIG_DIR}" ]]; then
	echo "Warning: ${CLAUDE_CONFIG_DIR} is missing; rebuild container to bind-mount host ~/.claude-personal." >&2
elif [[ ! -f "${CLAUDE_CONFIG_DIR}/.claude.json" ]]; then
	echo "Warning: no ${CLAUDE_CONFIG_DIR}/.claude.json; run 'claude' once on the host to authenticate." >&2
else
	echo "Claude credentials available at ${CLAUDE_CONFIG_DIR}"
fi

if command -v claude >/dev/null 2>&1; then
	echo "Claude Code already installed: $(claude --version 2>/dev/null || echo 'version unknown')"
	exit 0
fi

echo "Installing Claude Code ..."
curl -fsSL https://claude.ai/install.sh | bash

if ! command -v claude >/dev/null 2>&1; then
	echo "Claude Code install finished but 'claude' is not on PATH." >&2
	echo "Ensure ~/.local/bin is in PATH, then open a new shell." >&2
	exit 1
fi

echo "Claude Code installed: $(claude --version)"
