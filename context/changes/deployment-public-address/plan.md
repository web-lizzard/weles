# Public Address for the Hosted Instance Implementation Plan

## Overview

Slice S-08 of the `deployment` effort delivers the effort's outcome: the author and the certification reviewer use the hosted instance through the TUI at a public HTTPS address. The frame constrains that address. It cannot be derived by enumerating a shared-domain naming pattern, it does not surface in public certificate logs, and the public repository names no instance (auth-flow FR-07).

The mechanism is a remotely-managed Cloudflare Tunnel. A `cloudflared` sidecar joins the S-05 compose stack and connects outbound only. The instance lives under a random first-level label on a new neutral domain, served by Cloudflare's Universal SSL wildcard certificate, so public CT logs show only the apex and `*.<domain>`.

Execution state lives in `todos.md`, sibling of this file.

## Current State Analysis

- S-05 (`deployment-manual-deploy`) runs `postgres` and `api` as a compose stack on Mikrus, both published on `127.0.0.1` only. The author reaches the API over `ssh -L 8000:127.0.0.1:8000`. S-05 is still implementing: `deploy/compose.yml` and `deploy/remote-deploy.sh` arrive in its Phase 4.
- `README.md:32-69` already holds the "Hosting on Mikrus" runbook, and its "Access" subsection names only the SSH tunnel.
- Attempt limits key on an `AttemptSource` resolved from the TCP peer and `X-Forwarded-For`. Behind a proxy that is not trusted, every client shares one bucket.
- auth-flow S-01, S-04, and S-05 are `done`, so the slice's outside gate is met.
- There is no domain, no Cloudflare account, and no tunnel.

## Desired End State

The author runs `weles instance set https://<label>.<domain>`, signs in, and captures, and the reviewer does the same with the address received through the private certification submission.

- **Discovery:** crt.sh for `%.<domain>` lists only certificates for `<domain>` and `*.<domain>`. The repository contains no domain, label, or tunnel token.
- **Exposure:** the VPS opens no new listening port. `cloudflared` reaches Cloudflare outbound, and `api` stays published on `127.0.0.1:8000` as the SSH fallback.
- **Attempt limits:** each client network gets its own sign-in and registration bucket.
- **Deploy:** the API switch and its rollback depend on `api` health alone. A stack without `/srv/weles/cloudflared.env` deploys exactly as S-05 did.

### Key Discoveries:

- `backend/src/adapters/auth/source.py:20-24`: `X-Forwarded-For` is read only when the peer is trusted, walked right to left. Cloudflare appends the real client IP as the right-most entry and `cloudflared` adds no hop, so a single trusted sidecar address resolves the real client with no code change.
- `backend/src/config/settings.py:52`: `auth_trusted_proxy_addresses: list[str]`, set as `AUTH_TRUSTED_PROXY_ADDRESSES=["172.30.238.10"]` (JSON list, verified).
- `backend/Dockerfile:21`: uvicorn keeps its default `--proxy-headers` with `--forwarded-allow-ips` at `127.0.0.1`. The sidecar peer is not `127.0.0.1`, so `request.client` stays the sidecar and the app's own resolver decides.
- `backend/src/adapters/http/capture.py:54-57`: the reply route streams `text/event-stream` through `fastapi.sse` 0.141.1, which pings idle streams every 15 s. That is well under Cloudflare's 125 s read timeout, and tunnel responses with that content type are not buffered.
- `context/changes/deployment-manual-deploy/plan.md:244-249`: `remote-deploy.sh` runs `docker compose up -d --wait` over the whole stack and rolls back the API on failure. An unhealthy tunnel would roll back a healthy API.
- `research.md` (this change) and the S-08 planning research: Universal SSL on a full-setup Free zone covers the apex and first-level subdomains. Total TLS, Advanced Certificate Manager, second-level labels, and CNAME (partial) setup each issue certificates naming the host.
- `cloudflare/cloudflared` images are distroless (no shell). `cloudflared tunnel --metrics <addr> ready` (since 2024.11.1) exits non-zero unless `/ready` returns 200, which makes an exec-form healthcheck possible.

## What We're NOT Doing

- Flooding protection, WAF or rate-limiting rules, and Cloudflare Access (frame defers flooding protection).
- Changing backend code: no switch to `CF-Connecting-IP`, no `--proxy-headers` or `--forwarded-allow-ips` change, no disabling of `/docs` in prod.
- Removing the `127.0.0.1:8000` publish or the SSH access path.
- Tailscale, proxied AAAA, `wykr.es`, or quick tunnels.
- Forcing the tunnel protocol in the repository. The runbook documents the env override instead.
- A Mikrus 3.0 upgrade, which stays an escalation path.
- Amending the effort frame or roadmap, including S-05's Neon deviation.

## Implementation Approach

Three phases, in two delivery parts:

1. **Part one, no domain needed:** Phase 1 changes the stack, the deploy script, and the runbook. Deployed without a tunnel env file, the instance behaves exactly as under S-05.
2. **Part two, once the domain is bought:** Phase 2 prepares Cloudflare and the VPS from the runbook. Phase 3 deploys again and verifies the public address end to end.

The tunnel's hostname and ingress rule live in the Cloudflare dashboard, and its token lives in a mode-600 file on the VPS. Nothing identifying the instance enters the repository. None of the phases has a pre-code observable outcome to assert (compose, shell wiring, runbook, external setup), so none carries a `#### Tests` row.

Implementation starts only once S-05 is done, because Phase 1 edits files S-05's Phase 4 creates.

## Critical Implementation Details

- **Part one must load without the token.** `cloudflared` is in compose profile `tunnel`, with `env_file` in long form and `required: false` (Compose 2.24+). Otherwise, before Phase 2, loading the project fails and every deploy breaks.
- **Networks.** Listing `networks:` on a service drops it from `default`. `api` must list both `default` (to reach `postgres`) and `edge` (to be reached by `cloudflared`).
- **Healthcheck.** The image has no shell, so the healthcheck must use exec form (`CMD`). It must also pass `--metrics 127.0.0.1:20241` explicitly, matching the address in `command`.

## Phase 1: Tunnel Sidecar in the Stack

### Overview

The stack gains an optional `cloudflared` service, the deploy script stops coupling the API switch to the tunnel, and the runbook covers the public address. Deployed before any tunnel exists, nothing observable changes.

### Changes Required:

#### 1. Host stack

**File**: `deploy/compose.yml`

**Intent**: Declare the tunnel sidecar and the network through which it alone reaches the API, at a fixed address the backend can trust.

**Contract**:

- **Network `edge`:** a user-defined bridge with `ipam.config[].subnet: 172.30.238.0/24`.
- **Service `api`:**
  - `networks: [default, edge]`.
  - Everything else unchanged from S-05, including the `127.0.0.1:8000:8000` publish.
- **Service `postgres`:** unchanged, on `default` only.
- **Service `cloudflared`:**
  - Image `cloudflare/cloudflared:2026.9.1`, pinned exactly and never `latest`.
  - `profiles: [tunnel]`.
  - `env_file: [{ path: /srv/weles/cloudflared.env, required: false }]`.
  - `command: tunnel --no-autoupdate --metrics 127.0.0.1:20241 run`.
  - `networks: { edge: { ipv4_address: 172.30.238.10 } }`.
  - `healthcheck.test: ["CMD", "cloudflared", "tunnel", "--metrics", "127.0.0.1:20241", "ready"]`, with `start_period: 20s`.
  - `mem_limit: 128m`, `restart: unless-stopped`, and the same `json-file` log caps as the other services.
  - No `ports`.

#### 2. Remote switch script

**File**: `deploy/remote-deploy.sh`

**Intent**: Let only API health decide success and rollback, then bring the tunnel up when it is configured, without ever failing a switched deploy over it.

**Contract**:

- Every `up` in the switch and in the rollback targets `api` explicitly: `docker compose -f /srv/weles/compose.yml up -d --wait --wait-timeout 120 api`. Its `postgres` dependency still starts and is waited on.
- After a successful switch:
  - If `/srv/weles/cloudflared.env` exists, run `docker compose -f /srv/weles/compose.yml --profile tunnel up -d cloudflared`, then print `docker compose ps cloudflared`.
  - If that command fails, print a `::warning::` line and keep exit code 0.
  - Without the file, print `tunnel not configured, skipping cloudflared`.
- Image cleanup and the `deployed_sha` write are unchanged from S-05.

#### 3. Hosting runbook

**File**: `README.md`

**Intent**: A first-time Cloudflare user can take the instance public without leaking its hostname, and knows both access paths. It names no domain, label, or token.

**Contract**:

- **"One-time setup":** a step requiring `docker compose version` 2.24 or newer.
- **New subsection "Public address"** under "Hosting on Mikrus", in order:
  1. Register a new neutral domain with WHOIS privacy.
  2. Add it to Cloudflare Free as a full (nameserver) setup, never CNAME, and enable DNSSEC.
  3. In SSL/TLS → Edge Certificates, confirm the certificate lists only `<domain>` and `*.<domain>` and that Total TLS is off. Never buy Advanced Certificate Manager for this zone.
  4. Generate the label with `openssl rand -hex 12` and use it as a first-level name only, never `a.b.<domain>`.
  5. Create a remotely-managed tunnel with public hostname `<label>.<domain>` → `http://api:8000`.
  6. On the VPS:
     - Check that `docker network inspect $(docker network ls -q) | grep Subnet` shows no overlap with `172.30.238.0/24`.
     - Write `/srv/weles/cloudflared.env` with `TUNNEL_TOKEN=…`, `chmod 600`.
     - Add `AUTH_TRUSTED_PROXY_ADDRESSES=["172.30.238.10"]` to `backend.env`.
  7. Dispatch `deploy` for the current gated SHA so the tunnel starts.
  8. Share the address only through the private certification submission.
  - **Troubleshooting:** repeated tunnel disconnects → add `TUNNEL_TRANSPORT_PROTOCOL=http2` to `cloudflared.env` and restart `cloudflared`.
- **"Access":** `weles instance set https://<label>.<domain>` is the primary path, and the existing SSH tunnel stays as the fallback.
- **"Resources":** `cloudflared` appears in `docker stats`, capped at 128 MB.

### Success Criteria:

#### Automated Verification:

- A YAML check of `deploy/compose.yml` confirms:
  - `cloudflared` uses a pinned `cloudflare/cloudflared:<version>` tag, sits in profile `tunnel`, has an exec-form healthcheck, and publishes no ports.
  - `cloudflared` is attached to `edge` at `172.30.238.10`, inside the declared subnet.
- A YAML check confirms `api` lists both `default` and `edge`, and that `cloudflared`'s `env_file` entry has `required: false`.
- `uvx --from shellcheck-py shellcheck deploy/remote-deploy.sh` reports no findings.
- `remote-deploy.sh` passes `api` to every `up --wait`, and starts `cloudflared` only inside a check for `/srv/weles/cloudflared.env`.
- `git grep -nE 'cfargotunnel|TUNNEL_TOKEN=[^.<]|trycloudflare'` finds no tunnel identifier or token value.
- `README.md` has a "Public address" subsection naming no domain, label, or token.

#### Manual Verification:

- On the VPS, `docker compose version` reports 2.24 or newer.
- With no `/srv/weles/cloudflared.env`, dispatching `deploy` for the gated SHA carrying this phase:
  - ends green;
  - the log prints `tunnel not configured, skipping cloudflared`;
  - `docker compose -f /srv/weles/compose.yml ps` shows `api` and `postgres` healthy and no `cloudflared`;
  - the TUI still works over `http://localhost:8000` through the SSH tunnel.

---

## Phase 2: Cloudflare and VPS Bootstrap

### Overview

The author follows the "Public address" runbook up to the deploy step. At the end, the domain, certificate, and tunnel exist, and the VPS holds the token and trusts the sidecar.

### Changes Required:

#### 1. External and host configuration

**File**: none in the repository. Cloudflare dashboard, `/srv/weles/cloudflared.env`, `/srv/weles/backend.env`.

**Intent**: Prepare everything the tunnel needs without writing anything identifying into the repository.

**Contract**: As listed in the Phase 1 runbook, steps 1–6.

### Success Criteria:

#### Manual Verification:

- `dig NS <domain>` returns Cloudflare nameservers, and `dig +dnssec <domain> SOA` returns an `RRSIG` record.
- SSL/TLS → Edge Certificates lists only `<domain>` and `*.<domain>` on every certificate, and Total TLS shows as off.
- Networks → Tunnels shows one tunnel whose public hostname is `<label>.<domain>`, with a 24-hex-character first-level label and service `http://api:8000`.
- On the VPS:
  - `ls -l /srv/weles/cloudflared.env /srv/weles/backend.env` shows both as `-rw-------`;
  - `grep AUTH_TRUSTED_PROXY_ADDRESSES /srv/weles/backend.env` prints `["172.30.238.10"]`.
- On the VPS, `docker network inspect $(docker network ls -q) --format '{{.Name}} {{range .IPAM.Config}}{{.Subnet}}{{end}}'` shows no network other than `weles_edge` overlapping `172.30.238.0/24`.

---

## Phase 3: Public Address Go-Live

### Overview

A deploy starts the tunnel, and the author checks the public address end to end: reachability, discovery, exposure, attempt limits, memory, and deploy independence.

### Changes Required:

#### 1. Go-live

**File**: none in the repository.

**Intent**: Confirm the slice's outcome on the real instance and record the figures.

**Contract**: Dispatch `deploy` for the current gated SHA, per runbook step 7. Record the memory figures in the change notes.

### Success Criteria:

#### Manual Verification:

- Dispatching `deploy` ends green, and `docker compose -f /srv/weles/compose.yml ps` shows `api`, `postgres`, and `cloudflared` all healthy.
- Streamed capture through the public address:
  - from a machine outside the VPS, `weles instance set https://<label>.<domain>` then sign-in succeeds;
  - a capture message shows its reply arriving incrementally rather than all at once;
  - `curl -sI https://<label>.<domain>/health` returns `200`.
- `https://crt.sh/?q=%25.<domain>` lists no certificate naming `<label>`.
- `ss -ltnp` on the VPS shows the same listeners as before this phase: `8000` and `5432` on `127.0.0.1` only.
- Attempt-limit buckets are separate per client network:
  - five wrong-password sign-ins from network A make the sixth attempt from A refused;
  - a correct sign-in from network B, such as a phone hotspot, still succeeds.
- `docker stats --no-stream` and `free -m` on the VPS show `cloudflared` under 128 MB and free memory left.
- A bad tunnel does not block a deploy. With `TUNNEL_TOKEN` deliberately corrupted in `cloudflared.env`, dispatching `deploy`:
  - still ends green, with `api` healthy on the new SHA and a tunnel warning in the log;
  - restoring the token and running `docker compose -f /srv/weles/compose.yml --profile tunnel up -d cloudflared` brings the address back.

---

## Testing Strategy

### Unit Tests:

None. No production code changes. `backend/tests/unit/auth/test_source.py:16` already pins the right-most untrusted `X-Forwarded-For` entry winning behind a trusted peer, which is the header shape Cloudflare produces.

### Integration Tests:

None added.

### Manual Testing Steps:

1. Deploy Phase 1 without a tunnel env file and confirm S-05 behaviour is unchanged.
2. Bootstrap the domain, the Cloudflare zone, the tunnel, and the VPS env files (Phase 2).
3. Deploy with the tunnel, then check the TUI over HTTPS, streaming, CT, listeners, attempt buckets, memory, and deploy independence (Phase 3).

## Performance Considerations

- **Memory:** `cloudflared` idles in the tens of MB, capped at 128 MB so a runaway buffer (upstream issue #1205) cannot starve Postgres or the API on Mikrus 2.1. The S-05 escalation signal (`OOMKilled`, climbing restarts) still applies.
- **Latency:** traffic now hairpins through Cloudflare's edge, adding a small round trip that is negligible for a TUI.
- **Streaming:** the 15 s SSE keepalive keeps capture replies under the 125 s read timeout. Request bodies are capped at 100 MB on the Free plan, far above any capture.

## Migration Notes

- **Two-part rollout:** Phase 1 can land and deploy before any domain exists. The tunnel starts on the first deploy after `/srv/weles/cloudflared.env` appears.
- **Rotating the address:** if the address leaks, change the public hostname in the tunnel to a new label, then send the new address privately. No redeploy is needed, because ingress lives in the dashboard.
- **Rotating the token:** replace `TUNNEL_TOKEN` in `cloudflared.env`, then `docker compose -f /srv/weles/compose.yml --profile tunnel up -d --force-recreate cloudflared`.
- **Schema:** no change.

## References

- Effort frame: `context/efforts/deployment/frame.md` (Boundaries: hard-to-discover address, FR-07 via auth-flow)
- auth-flow frame: `context/efforts/auth-flow/frame.md:19-21,44`
- Roadmap slice: `context/efforts/deployment/roadmap.md:157-173` (S-08)
- Research: `context/changes/deployment-public-address/research.md`
- Prerequisite plan: `context/changes/deployment-manual-deploy/plan.md` (Phase 4 compose and switch script)
- Cloudflare: Universal SSL coverage and limitations, Total TLS, tunnel troubleshooting (buffering, second-level subdomains), connection limits (125 s read timeout), HTTP headers (`X-Forwarded-For` append)
- cloudflared: release 2026.9.1, `tunnel ready` (PR #1135), distroless Dockerfile
