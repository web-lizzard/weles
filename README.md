# project-template

## Install the TUI

You need **Node.js 22** or newer.

```sh
npm i -g https://github.com/web-lizzard/weles/releases/latest/download/weles.tgz
weles instance set <address>
```

**Releasing a TUI version:** bump `version` in `tui/package.json`, commit, then push tag `tui-v<version>` (for example `tui-v0.1.0`). The `tui-release` workflow attaches `weles-<version>.tgz` and `weles.tgz` to a GitHub Release.

## Bringing a hosted database to a commit's schema

The app does not migrate on startup. Bring the hosted database to the schema a commit expects with one script:

1. Check out the commit you are about to deploy.
2. Get the database's **direct** connection string — not a `-pooler` one. Migrations need the direct host; the script refuses a pooler URL. In the Neon console, copy the branch's direct connection string. Over an SSH tunnel to a self-hosted Postgres (see "Hosting on Mikrus" below), the form is `postgresql://<user>:<password>@127.0.0.1:5432/<db>`.
3. Run the script with the connection string set inline:

   ```sh
   cd backend && NEON_DIRECT_URL='<direct connection string>' uv run python scripts/migrate_database.py
   ```

   It prints the target (password hidden) and `current → head`, asks you to type the database name, and applies every pending revision in one transaction. An up-to-date database exits without prompting. Pass `--yes` to skip the prompt.

Run it **before** deploying a commit that adds migration revisions: the deployed app expects the new schema as soon as it starts.

Never put `NEON_DIRECT_URL` in `backend/.env`. `Settings` forbids unknown keys, so the app would fail to start.

## Hosting on Mikrus

The production backend and its Postgres run as a Docker Compose stack on a Mikrus VPS. The stack changes only when the `deploy` workflow is dispatched for a `main` commit whose required checks and `integration` status both passed.

### One-time setup

1. **SSH access.** Log in with a dedicated deploy key on port `10000 + <machine number>` — Mikrus never exposes port 22.
2. **Docker.** Install Docker Engine with the Compose plugin; `docker compose version` must print a v2 version.
3. **Disk.** Mount the added data disk at `/srv/weles` and create `/srv/weles/pgdata`.
4. **Env files**, both `chmod 600`:
   - `/srv/weles/postgres.env` — `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
   - `/srv/weles/backend.env` — `DATABASE_URL=postgresql+asyncpg://…@postgres:5432/…`, `AUTH_SIGNING_SECRET`, `ENVIRONMENT_NAME=prod`, `OPENROUTER_API_KEY`, and the Langfuse keys.
5. **Base image.** `docker pull pgvector/pgvector:pg16`.
6. **GitHub environment.** Create a `production` environment holding `DEPLOY_SSH_HOST`, `DEPLOY_SSH_PORT`, `DEPLOY_SSH_USER`, `DEPLOY_SSH_KEY`, and `DEPLOY_SSH_KNOWN_HOSTS` (from `ssh-keyscan -p <port> <host>`).

### Deploy

Dispatch `integration` for the target SHA, then dispatch `deploy` with the same SHA.

### Migrate

Open a tunnel — `ssh -L 5432:127.0.0.1:5432 …` — then run the migration script above from a checkout of the deployed SHA, with `NEON_DIRECT_URL=postgresql://…@127.0.0.1:5432/<db>`. On a first deploy, follow it with `docker compose -f /srv/weles/compose.yml restart api` so the API restarts against the now-migrated schema.

### Access

Open a tunnel — `ssh -L 8000:127.0.0.1:8000 …` — then `weles instance set http://localhost:8000`.

### Rollback

Dispatch `deploy` with an older gated SHA.

### Backup

Over SSH: `docker compose -f /srv/weles/compose.yml exec postgres pg_dump -U <user> <db> > backup.sql`.

### Resources

`docker stats --no-stream` and `free -m` on the VPS. Escalate to a larger Mikrus plan when `docker inspect` shows `OOMKilled` or container restart counts climb.

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

## Langfuse MCP (Claude Code and Cursor)

Embedding traces from the backend land in [Langfuse Cloud](https://cloud.langfuse.com). Both editors can query the same project through Langfuse’s hosted MCP server at `https://cloud.langfuse.com/api/public/mcp` (streamable HTTP, Basic auth).

| File | Editor |
| --- | --- |
| `.mcp.json` | Claude Code (`/mcp`) |
| `.cursor/mcp.json` | Cursor MCP panel |

Neither file commits secrets. Langfuse keys live in `backend/.env` (same as OTLP smoke traces).

**Claude Code** — `.mcp.json` uses `headersHelper` (`scripts/langfuse-mcp-auth-headers.sh`) to build Basic auth from `backend/.env` on each connect. Restart Claude Code or reconnect MCP after changing keys.

**Cursor** — `.cursor/mcp.json` declares `"type": "stdio"` and runs `scripts/langfuse-mcp-cursor.sh` (stdio → `mcp-remote` → Langfuse HTTP). Keys come from `backend/.env` via `scripts/langfuse-mcp-refresh-headers.sh` (gitignored `.cursor/langfuse-mcp.headers`).

Troubleshooting Cursor:

1. Workspace root must be the repo (`/workspaces/weles`), not `backend/` — otherwise `.cursor/mcp.json` is ignored.
2. **Project MCP is not under Settings → Tools.** Use the sidebar **Customize → MCPs** (or `Cmd/Ctrl+Shift+P` → **Open Customize** → **MCPs**). At the top, open the **scope** dropdown and pick this repo folder (not only **User**). Marketplace plugins (Exa, GitLens) are separate from your `langfuse` server.
3. On Cursor **3.15–3.16** and in **devcontainers**, project servers often **do not render** in Customize even when configured — update to **3.17+** if you can. Workaround: run `bash scripts/register-langfuse-mcp-user.sh` (writes `langfuse` into `~/.cursor/mcp.json` on the machine that runs MCP — inside the container that is `/home/vscode/.cursor/mcp.json`), then **Developer: Reload Window**.
4. If the server appears but fails to start, open its network/sandbox setting and choose **Allow all** (stdio `mcp-remote` needs outbound HTTPS).
5. **Editor Agent (Ctrl+I)** / chat in the editor window — the separate **Agents** window may not load project MCP on remote/devcontainer setups.
6. **Output → MCP Logs** while toggling `langfuse` on; test manually: `bash scripts/langfuse-mcp-cursor.sh` (should log “Proxy established successfully”).

Derive manually from project API keys (`public_key:secret_key`, colon, no newline):

```bash
echo -n "pk-lf-xxx:sk-lf-xxx" | base64 -w 0
```

Use the **EU** endpoint above if your project is on `cloud.langfuse.com`; US projects need `https://us.cloud.langfuse.com/api/public/mcp` in both MCP configs.
