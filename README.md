# project-template

## Dev container: Ordo (skills)

On **Rebuild Container**, `postCreateCommand` runs `.devcontainer/post-create.sh`, which executes every `*.sh` script in `post-create.d/` in sorted order. Step **`08-install-ordo.sh`** installs [`@web-lizzard/ordo`](https://github.com/web-lizzard/ordo) globally so `ordo` is available in the integrated terminal.

### Setup

1. Copy `.env.example` to `.env` and set `GITHUB_PACKAGES_TOKEN` to a **classic** GitHub PAT with the `read:packages` scope.
2. Rebuild the dev container. On the host, `initialize.d/05-sync-devcontainer-env.sh` copies the token into `.devcontainer/devcontainer.env`, which Docker injects via `runArgs` (`localEnv` in `devcontainer.json` does **not** read `.env` on its own).
3. Inside the container, verify: `ordo status`

### Managing skills

Ordo pulls skills and related artifacts from the internal GitHub repository:

```sh
ordo add <capability>       # install capability artifacts (e.g. skills)
ordo status                 # list installed capabilities and versions
ordo update                 # update within installed major versions
ordo remove <capability>    # remove a capability
```

Installed skills land under `.cursor/skills/` (gitignored).

## Dev container: post-create setup

On **Rebuild Container**, `postCreateCommand` also runs:

- **`10-pre-commit.sh`** — installs [pre-commit](https://pre-commit.com/) and registers git hooks. The repo config (`.pre-commit-config.yaml`) starts with trailing-whitespace only; extend hooks as the project grows.
- **`15-install-claude-code.sh`** — installs Claude Code CLI (credentials bind-mounted from host `~/.claude-personal`).

Add new in-container setup steps as numbered scripts in `.devcontainer/post-create.d/`.
