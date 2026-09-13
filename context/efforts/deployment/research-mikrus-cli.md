---
date: 2026-09-13T17:38:00+02:00
topic: "Mikrus CLI and API for VPS interaction versus SSH-based deploy"
topic_slug: mikrus-cli
container_id: deployment
tags: [research, mikrus, cli, api, vps, docker, deploy, ssh]
last_updated: 2026-09-13
---

# Research: Mikrus CLI and API for VPS interaction versus SSH-based deploy

## Research Question

/research deployment --topic mikrus-cli sprawdź czy cli zapewnia jakieś wygodne cli do interakcji z vps

## Summary

Mikrus does **not** ship a single branded “Mikrus CLI” product on [wiki.mikr.us](https://wiki.mikr.us/) or [mikr.us](https://mikr.us/). Programmatic VPS interaction is the **official HTTP API** at [api.mikr.us](https://api.mikr.us/) (API key from [mikr.us/panel/?a=api](https://mikr.us/panel/?a=api)). The closest operator-adjacent client is the **bash `mikrus` script** in [unkn0w/noobs](https://github.com/unkn0w/noobs), installed via `chce_mikrus_cli.sh`; **community Rust/Go CLIs** (notably [pwittchen/mikrus-cli](https://github.com/pwittchen/mikrus-cli)) wrap more API endpoints plus SSH shortcuts.

These tools are **convenient for control-plane tasks** (restart, stats, ports, logs, short remote `exec`, cloud subdomain assignment via `/domain`) but **not a substitute for SSH + Docker** for day-to-day Weles deploys: official docs recommend **SCP** for file upload, **`exec` is capped at 60 seconds**, there is **no Docker API**, and long-running compose/migration work belongs on an interactive SSH session.

**Weles** documents Mikrus hosting in sibling research only; it **does not integrate** Mikrus CLI. Planned deploy flow remains **`docker pull` / `docker run` (or compose) over SSH** plus **panel or wykr.es** for public URL (`context/efforts/deployment/research.md`).

## Findings

### Official API — the real interface

The authoritative surface is **“API systemu MIKR.US”** at [https://api.mikr.us/](https://api.mikr.us/). Authentication requires POST with server name in `srv` and key in `key` or `Authorization` header; the key is issued in the panel API page.

Documented modules include `/info`, `/serwery`, `/restart`, `/logs`, `/amfetamina`, `/db`, `/exec`, `/upload`, `/stats`, `/porty`, `/cloud`, and `/domain` (assign a cloud subdomain to a port). Limits quoted on the same page: do not flood requests; **`exec` timeout 60s**; **`upload` max 20 files, 20 MB total**; several endpoints note **cache=60s**.

There is **no API module for Docker** — container lifecycle on the VPS is done via SSH (or short `exec` commands within the time limit).

### Bash `mikrus` (NOOBS reference client)

NOOBS scripts are documented on the wiki ([skrypty NOOBS](https://wiki.mikr.us/skrypty_noobs/)); new servers may receive `/opt/noobs`, and manual install uses `curl -s https://noobs.mikr.us | bash` per [unkn0w/noobs](https://github.com/unkn0w/noobs).

The **`mikrus`** bash client ([mikrus-cli/mikrus](https://github.com/unkn0w/noobs/blob/main/mikrus-cli/mikrus)) exposes: `info`, `servers`, `restart`, `logs`, `amfetamina`, `db`, `exec --cmd`, `stats`, `ports`. Installer [chce_mikrus_cli.sh](https://github.com/unkn0w/noobs/blob/main/scripts/chce_mikrus_cli.sh) writes `~/.mikrus_cli.conf`, copies the script to `/usr/bin/mikrus`, and installs `jq` via `apt` — usage: `./chce_mikrus_cli.sh -s [nazwa_serwera] -k [api_key]`.

Compared to the full API, this script **does not wrap** `/upload`, `/cloud`, or `/domain`.

### On-server `domena` vs API `/domain`

Sibling deploy research notes panel subdomains and **`mikrus.cloud` / CLI `domena`** often require the app to listen on **IPv6** (`context/efforts/deployment/research.md`). The wiki describes the on-box **`domena`** tool for quick subdomains ([szybka subdomena](https://wiki.mikr.us/szybka_subdomena/)): “możesz zrobić to za pomocą naszego narzędzia o nazwie ‘domena’” and “Twoja aplikacja musi słuchać na adresacji IPv6”. That is **separate** from the bash `mikrus` client but is another “CLI-like” path for DNS on the VPS.

Community **pwittchen/mikrus-cli** adds `domain`, `cloud`, `ssh`, and `status` (infra from status.mikr.us) on top of the same API — the widest single third-party wrapper found in this research.

### Convenience for deploy ops vs SSH + Docker

**Where API/CLI helps:** restart without logging in; read stats/ports/logs; fetch DB credentials; temporary boost (`amfetamina`, with Frog/plan exclusions per [amfetamina wiki](https://wiki.mikr.us/amfetamina/)); one-shot automation via `exec`; assign cloud domains via `/domain` or pwittchen’s `domain`.

**Where SSH remains primary (official docs):** file transfer for deploys — [jak wysyłać pliki](https://wiki.mikr.us/jak_wysylac_pliki_na_mikrusa/) states “Sugerowanym rozwiązaniem przy uploadzie plików na serwer jest użycie SCP.” Interactive shell, `docker compose`, image pulls, and migrations exceed **`exec`’s 60s** limit. Panel **Dashboard** one-click custom commands ([dashboard wiki](https://wiki.mikr.us/dashboard/)) are another panel feature, not the bash CLI.

For **Weles on Mikrus** (one API container, GHCR pull, Neon `DATABASE_URL`), the documented v1 path is **`docker login`, pull, `docker run`**, subdomain via **panel** or **wykr.es** — not Mikrus CLI automation (`context/efforts/deployment/research.md`).

### Auth, networking, and plan constraints

- **Auth:** possession of the panel API key grants API access for the configured server context; bash client stores credentials in `~/.mikrus_cli.conf`.
- **SSH:** use the **assigned high port**, not 22 ([logowanie na serwery](https://wiki.mikr.us/logowanie_na_serwery/)): “Nie próbuj używać portu 22 do łączenia się z serwerem.”
- **IPv6:** servers run “głównie IPv6” ([o co chodzi z IPv6](https://wiki.mikr.us/o_co_chodzi_z_ipv6/)); subdomains and some cloud features assume IPv6 listeners.
- **Plans:** Docker from **Mikrus 2.1+**; smallest tier without Docker is documented on [mikr.us](https://mikr.us/) — relevant because Weles deploy research targets 2.1+ with Docker.

### Weles repository posture

No `mikrus`, `wykr.es`, or Mikrus CLI usage in application code. The **Ink TUI** is a local HTTP client to the Weles API (`tui/src/api/client.ts`), not VPS management. No production deploy scripts or `.github/workflows` yet — gaps called out in deploy research.

## Code References

- `context/efforts/deployment/research.md:36` — only in-repo mention of Mikrus-related CLI: “Panel subdomains and `mikrus.cloud` / CLI `domena` often require listening on **IPv6**”
- `context/efforts/deployment/research.md:93-94` — documented VPS ops: `docker login`, pull, run; panel subdomain assignment (no Mikrus CLI)
- `context/efforts/deployment/research.md:28` — no Dockerfile/workflow/compose in repo yet
- `tui/src/api/client.ts:27-29` — TUI `baseUrl` hardcoded to localhost (future `WELES_API_URL`, not Mikrus CLI)

## External References

- <https://api.mikr.us/> — official API modules, POST + `srv`/`key`, limits on `exec` (60s) and `upload` (20 files, 20 MB)
- <https://mikr.us/panel/?a=api> — API key issuance (linked from api.mikr.us)
- <https://github.com/unkn0w/noobs/blob/main/mikrus-cli/mikrus> — reference bash `mikrus` subcommands
- <https://raw.githubusercontent.com/unkn0w/noobs/main/scripts/chce_mikrus_cli.sh> — installer: `-s` server, `-k` API key, `~/.mikrus_cli.conf`, `/usr/bin/mikrus`
- <https://wiki.mikr.us/skrypty_noobs/> — NOOBS on new servers in `/opt/noobs`
- <https://github.com/pwittchen/mikrus-cli> — community CLI with `domain`, `cloud`, `ssh`, `status`
- <https://wiki.mikr.us/jak_wysylac_pliki_na_mikrusa/> — SCP recommended for uploads, not API CLI as primary deploy path
- <https://wiki.mikr.us/szybka_subdomena/> — on-server `domena` tool and IPv6 requirement
- <https://wiki.mikr.us/logowanie_na_serwery/> — SSH on assigned port, not 22

## Open Questions

- Whether Weles deployment automation should standardize on **pwittchen/mikrus-cli** (developer laptop) vs raw **`curl` to api.mikr.us** vs **panel-only** for subdomain/port setup — no product decision in this research.
- Whether **Dashboard** custom deploy buttons in the panel are sufficient for “one-click” restarts without maintaining CLI config on the VPS.
