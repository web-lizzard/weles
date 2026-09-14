---
date: 2026-09-14T20:15:00+02:00
topic: "Public HTTPS address for hosted Weles without wykr.es enumeration and CT exposure"
topic_slug: null
container_id: deployment-public-address
tags: [research, mikrus, cloudflare, tailscale, tls, tui, compose, auth]
last_updated: 2026-09-14
---

# Research: Public HTTPS address for hosted Weles without wykr.es enumeration and CT exposure

## Research Question

/research deployment-public-address Jak wystawić hostowaną instancję Weles (API na Mikrusie, 127.0.0.1:8000, VPS IPv6 + przekierowane porty IPv4) pod publicznym adresem HTTPS, którego nie da się znaleźć przez enumerację wspólnej domeny (nie serwer-port.wykr.es) i który nie pojawi się w publicznych logach certyfikatów (CT) — np. tunel Cloudflare z własną domeną i certyfikatem wildcard, Cloudflare proxy, subdomena Mikrusa, Tailscale Funnel; koszt, zużycie RAM na Mikrusie 2.1, wymagania TUI (http/https), --proxy-headers i auth_trusted_proxy_addresses w backendzie, oraz wpływ na deploy z S-05 (compose).

## Summary

Slice S-08 asks for a **hard-to-discover public HTTPS URL** for the author and certification reviewer (TUI), with **no wykr.es-style enumeration** and **no appearance in public Certificate Transparency (CT) logs** (`context/efforts/deployment/roadmap.md:170-172`). Those two constraints collide with **standard browser-trusted HTTPS** on a custom hostname: every publicly trusted certificate (Cloudflare Universal or wildcard edge certs, Let's Encrypt on the origin, Tailscale `*.ts.net`) is logged to public CT. Outbound **Cloudflare Tunnel** changes reachability (no inbound 443 on the VPS) but **does not** hide the edge certificate for `your-domain.example` from CT.

**Operational fit with S-05** (API + Postgres on loopback, no public bind today): add a **third runtime piece**—typically `cloudflared` as a compose service or host systemd unit—ingress to `http://api:8000` on the internal Docker network while keeping `postgres` and `api` off the public internet. Set **`AUTH_TRUSTED_PROXY_ADDRESSES`** to the tunnel/proxy peer so sign-in and registration attempt limits use real client IPs from `X-Forwarded-For`. **`--proxy-headers` on uvicorn** is still absent from the production image and is deferred from S-05 to this slice; attempt limiting does not depend on it because the app parses `X-Forwarded-For` explicitly when the TCP peer is trusted.

**TUI** already supports `http:` and `https:` instance URLs via `weles instance set`; HTTPS uses Node's default CA trust with no pinning.

**Cost on Mikrus 2.1:** VPS **75 PLN/year**; Cloudflare zone + tunnel on free tier (account limits include **1,000 tunnels** and **25 active replicas per tunnel**); domain registrar fee. **`cloudflared`** is lightweight (docs cite ~16 MB in an example); **`tailscaled`** is on the order of **~40 MB RES** on Linux per community profiling—not an official SLA.

**Planning tension:** literal **zero CT** plus **public HTTPS for an arbitrary reviewer with stock TUI** is not achievable with Web PKI. The slice either **narrows the CT requirement** (e.g. avoid wykr.es and do not advertise the URL, accepting CT for a random subdomain) or **changes the access model** (SSH tunnel, private CA, Tailscale-only tailnet). That choice belongs in `/plan deployment-public-address`.

## Findings

### Roadmap and prerequisites

- S-08 change `deployment-public-address` is materialized early but **implements only after S-05** (`deployment-manual-deploy`); S-05 leaves the API on `127.0.0.1:8000` with no reverse proxy (`context/changes/deployment-public-address/change.md:16-21`).
- S-05 explicitly excludes public address, reverse proxy, TLS, and `--proxy-headers` (`context/changes/deployment-manual-deploy/plan.md:43`).
- Planned compose: `postgres` and `api` published on **`127.0.0.1` only** (`context/changes/deployment-manual-deploy/plan.md:229-235`, `281`).

### Certificate Transparency vs exposure options

| Mechanism | Avoids `serwer-port.wykr.es` pattern? | Custom hostname in public CT? | TUI `https://` without extra trust |
|-----------|----------------------------------------|--------------------------------|-------------------------------------|
| Cloudflare Tunnel + own domain | Yes | **Yes** (edge public cert) | Yes |
| Cloudflare proxied AAAA (app on IPv6 :80) | Yes | **Yes** | Yes |
| Mikrus **wykr.es** | **No** (predictable `srvXX-20YYY.wykr.es`) | Under `*.wykr.es`, not your brand | Yes |
| Tailscale Funnel (`*.ts.net`) | Yes (different pattern) | **Yes** (Tailscale documents CT for machine names) | Yes |
| SSH `-L` only / no public URL | N/A | No public Web PKI cert | `http://localhost` via tunnel |

Cloudflare issues **publicly trusted** edge certificates for proxied or tunnel-published hostnames; CT monitoring alerts when such certs hit public logs ([CT monitoring](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/certificate-transparency-monitoring/), [Universal SSL](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/)). Tunnel routing still inherits hostname SSL/WAF at the edge ([routing to tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/)).

Tailscale HTTPS explicitly states machine names are **published in the public CT ledger** ([Set up HTTPS certificates](https://tailscale.com/docs/how-to/set-up-https-certificates)). Funnel exposes a stable public `*.ts.net` URL ([Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel)).

**Without public CT:** only non–Web-PKI trust (self-signed, enterprise CA). Stock TUI would fail TLS verification unless the reviewer installs trust—unsuitable for the certification path described in the roadmap unless the process changes.

**wykr.es** provides automatic HTTPS at the Mikrus edge with a **enumerable** name format (`serwer-numer_portu.wykr.es`) ([shared domain wiki](https://wiki.mikr.us/wspoldzielona_domena/))—it satisfies cheap HTTPS but **violates** the S-08 enumeration constraint.

### Mikrus 2.1: IPv6, ports, RAM

- **1 GB RAM**, **no stable file-backed SWAP** ([technical limits](https://wiki.mikr.us/ograniczenia_techniczne_mikrusa/)); plan S-05 already stacks API + Postgres on the VPS instead of Neon.
- IPv4 uses forwarded high ports (`10000+ID`, `20000+ID`, `30000+ID`); IPv6-first hosting ([IPv6 wiki](https://wiki.mikr.us/o_co_chodzi_z_ipv6/)).
- **Tunnel** uses **outbound-only** `cloudflared` connections—no need to expose world-reachable 443 on the VPS ([Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)), aligned with Mikrus guides ([tunnel on Mikrus](https://wiki.mikr.us/podpiecie_domeny_przez_tunel_cloudflare/)).
- **Orange-cloud AAAA** alternative: app listens on **port 80 on IPv6** with Cloudflare terminating TLS ([Cloudflare on Mikrus](https://wiki.mikr.us/podpiecie_domeny_przez_cloudflare/)).
- `cloudflared` is documented as lightweight (example **~16.3M** memory in systemd status); large Zero Trust deployments cite **4 GB+** hosts—that scale does not apply to a single tunnel on 2.1 ([system requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-availability/system-requirements/)).
- Free-tier tunnel account limits: **1,000 tunnels per account**, **25 active replicas per tunnel** ([account limits](https://developers.cloudflare.com/cloudflare-one/account-limits/)).

### Backend: `auth_trusted_proxy_addresses` and `--proxy-headers`

- Setting default: empty list `auth_trusted_proxy_addresses` (`backend/src/config/settings.py:52`), env `AUTH_TRUSTED_PROXY_ADDRESSES` per auth-flow plan.
- `get_trusted_proxy_addresses()` feeds sign-in/register `attempt_source` (`backend/src/adapters/auth/compose.py:70-73`, `backend/src/adapters/auth/router.py:53-65`).
- `resolve_attempt_source` trusts `X-Forwarded-For` only when the TCP **peer** is in `trusted_proxies`, walking the header right-to-left (`backend/src/adapters/auth/source.py:4-24`). Untrusted peers ignore the header entirely.
- Without trusted proxy configuration behind a single edge IP, **all clients share one attempt-limit bucket** (hosted deployment note in `context/changes/auth-flow-attempt-limits/plan.md` around line 499).
- Production **uvicorn** command has **no** `--proxy-headers` (`backend/Dockerfile:21`). Effort research recommends adding it behind a reverse proxy (`context/efforts/deployment/research.md:40`). For Weles rate limits, explicit XFF parsing is the critical piece; `--proxy-headers` mainly affects how Starlette populates `request.client` for other middleware.
- When `cloudflared` runs as a compose sidecar, trusted addresses should be the **sidecar container IP** on the Docker bridge (or documented gateway), verified after S-05 lands.

### TUI requirements

- Instance address persisted in XDG config; CLI `weles instance set <url>` (`tui/src/instance/configStore.ts`, `tui/src/instance/command.ts`).
- Only **`http:`** and **`https:`** schemes; optional path prefix for API root (`tui/src/instance/address.ts:18-50`).
- HTTP client uses default `fetch` with **no custom TLS agent or CA pinning** (`tui/src/api/client.ts`)—public HTTPS must use a **publicly trusted** cert chain.

### Impact on S-05 compose and deploy

- S-05 plans `deploy/compose.yml` with two services and loopback port maps; deploy workflow copies compose + `remote-deploy.sh` (`context/changes/deployment-manual-deploy/plan.md:221-266`).
- S-08 likely **extends** compose with `cloudflared` (or equivalent), adds tunnel credentials/config on the VPS, and updates the runbook from SSH tunnel + `http://localhost:8000` to `weles instance set https://<chosen-host>`.
- API may drop host publish `127.0.0.1:8000` in favor of **internal-only** `api:8000` if only the tunnel reaches it; keep loopback publish if operators still want local SSH health checks without the tunnel.
- No change to S-05 deploy gate logic; tunnel config is **orthogonal** to image SHA streaming unless secrets or compose paths are added to `scp` in the deploy job.
- Prior effort research notes compose eases later **nginx** or **cloudflared** (`context/efforts/deployment/research.md:112`). **Tailscale** is not mentioned elsewhere in `context/`.

### Cost sketch

| Item | Typical cost |
|------|----------------|
| Mikrus 2.1 | 75 PLN/year ([mikr.us](https://mikr.us/)) |
| Cloudflare DNS + Tunnel | $0 on free tier (tunnel/replica limits above) |
| Own domain | Registrar-dependent |
| Tailscale Funnel | Personal/free tier for small use; Funnel is public-by-URL |

## Code References

- `context/efforts/deployment/roadmap.md:157-173` — S-08 outcome, wykr.es and CT constraints
- `context/changes/deployment-public-address/change.md:16-21` — S-05 prerequisite, loopback API assumption
- `context/changes/deployment-manual-deploy/plan.md:43` — proxy/TLS out of scope for S-05
- `context/changes/deployment-manual-deploy/plan.md:229-235` — planned loopback compose ports
- `backend/src/config/settings.py:52` — `auth_trusted_proxy_addresses`
- `backend/src/adapters/auth/source.py:4-24` — X-Forwarded-For trust rules
- `backend/src/adapters/auth/router.py:53-65` — `attempt_source` wiring
- `backend/src/adapters/auth/compose.py:70-73` — settings-backed trusted proxies
- `backend/Dockerfile:21` — uvicorn without `--proxy-headers`
- `tui/src/instance/address.ts:18-50` — http/https parsing and normalization
- `tui/src/api/client.ts` — default fetch, no custom TLS
- `context/efforts/deployment/research.md:36-40` — Mikrus HTTPS paths and proxy-headers note

## External References

- https://developers.cloudflare.com/ssl/edge-certificates/additional-options/certificate-transparency-monitoring/ — public CA certs for monitored domains appear in CT logs
- https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/ — Universal SSL is publicly trusted at the edge
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/ — outbound-only tunnel to Cloudflare
- https://developers.cloudflare.com/cloudflare-one/account-limits/ — tunnel count and replica limits
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-availability/system-requirements/ — cloudflared sizing examples
- https://tailscale.com/docs/how-to/set-up-https-certificates — Tailscale HTTPS and CT ledger for `*.ts.net`
- https://tailscale.com/docs/features/tailscale-funnel — public Funnel URLs and TLS
- https://wiki.mikr.us/wspoldzielona_domena/ — wykr.es HTTPS and name pattern
- https://wiki.mikr.us/podpiecie_domeny_przez_tunel_cloudflare/ — Mikrus + Cloudflare Tunnel
- https://wiki.mikr.us/podpiecie_domeny_przez_cloudflare/ — AAAA + proxied Cloudflare on Mikrus
- https://wiki.mikr.us/ograniczenia_techniczne_mikrusa/ — RAM and SWAP limits
- https://fastapi.tiangolo.com/deployment/docker/ — `--proxy-headers` behind reverse proxies

## Open Questions

- Whether **“no CT”** is literal (blocks all Web PKI options) or means **avoid wykr.es** plus **do not publish the URL** (CT still lists a random subdomain cert).
- Preferred mechanism after constraint clarification: **Cloudflare Tunnel** vs **proxied AAAA** vs **Tailscale Funnel** vs non-public access.
- Exact **`AUTH_TRUSTED_PROXY_ADDRESSES`** values for the chosen sidecar (Docker network IPs vs `127.0.0.1` for host-run `cloudflared`).
- RAM headroom on **2.1** with Postgres + API + tunnel under capture/SSE load—upgrade to **3.0 (130 PLN/year)** or not.
- Whether deploy workflow should **version tunnel config** in-repo vs manual one-time VPS setup.
