FROM mcr.microsoft.com/devcontainers/base:ubuntu

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
	&& apt-get install -y --no-install-recommends zsh \
	&& rm -rf /var/lib/apt/lists/*

# Default login shell for the devcontainer user (Cursor integrated terminal picks this up too).
RUN chsh -s /usr/bin/zsh vscode

COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /usr/local/bin/

# User-local CLIs (ordo, Claude Code) without breaking the image PATH in containerEnv.
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Required so host ~/.claude-personal can be bind-mounted for Claude Code credentials.
RUN mkdir -p /home/vscode/.claude-personal && chown -R vscode:vscode /home/vscode/.claude-personal
