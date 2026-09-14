# Public Address for the Hosted Instance — Plan Brief

> Full plan: `plan.md`

## What & Why

The author and the certification reviewer need to use the hosted Weles instance through the TUI at a public HTTPS address. The frame requires that address to be hard to discover: no shared-domain enumeration, nothing in public certificate logs, and nothing naming it in the repository.

## Starting Point

S-05 runs `postgres` and `api` in compose on Mikrus, bound to `127.0.0.1`, reached over SSH tunnels. Proxy-aware attempt limiting exists in the backend but trusts no proxy yet.

## Desired End State

`weles instance set https://<random-label>.<neutral-domain>` works from anywhere, including capture streaming. Public CT logs show only `<domain>` and `*.<domain>`, the VPS opens no new port, and each client network gets its own attempt-limit bucket. Deploys still switch and roll back on API health alone.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Mechanism | Cloudflare Tunnel as a `cloudflared` compose sidecar | Outbound-only, no inbound port, IP hidden, ~tens of MB RAM. | Plan |
| CT exposure | New neutral domain, 24-hex first-level label under the Universal SSL wildcard | CT then lists only the apex and wildcard, and the domain hints at nothing. | Plan |
| Hostname leak guards | Full DNS setup, DNSSEC on, Total TLS/ACM off, no second-level labels | Each of those alternatives issues a certificate naming the host. | Research |
| Tunnel config | Remotely managed: token file on VPS, hostname and ingress in dashboard | The repository never learns the hostname (FR-07). | Plan |
| Loopback publish | Keep `127.0.0.1:8000` and SSH access as fallback | Diagnostics and access survive a Cloudflare outage. | Plan |
| Client IP trust | Fixed sidecar IP `172.30.238.10` in `AUTH_TRUSTED_PROXY_ADDRESSES`, no code change | Cloudflare appends the client as the right-most XFF entry, and the resolver already walks right to left. | Research |
| `--proxy-headers` | Unchanged | uvicorn only trusts `127.0.0.1`, so the app resolver alone decides. | Research |
| Deploy coupling | `up --wait api` gates switch and rollback; tunnel started afterwards, warning only | A Cloudflare problem must not roll back a healthy API. | Plan |
| Two-part delivery | `cloudflared` in profile `tunnel` with optional env file | Phase 1 deploys before a domain exists without breaking. | Plan |

## Scope

**In scope:** `deploy/compose.yml` sidecar and `edge` network, `deploy/remote-deploy.sh` gating, README "Public address" runbook, Cloudflare and VPS bootstrap, go-live verification.

**Out of scope:** WAF, rate-limit rules, Cloudflare Access, backend code changes (`CF-Connecting-IP`, `/docs`), removing SSH access, other mechanisms (Tailscale, AAAA, wykr.es), Mikrus 3.0, and frame or roadmap amendments.

## Architecture / Approach

```
TUI ──HTTPS──▶ Cloudflare edge (*.domain cert) ◀──outbound tunnel── cloudflared (172.30.238.10, net edge)
                                                                        │ http://api:8000
                                                  api (default + edge, 127.0.0.1:8000) ── postgres (default)
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Tunnel Sidecar in the Stack | Optional sidecar, API-only deploy gating, runbook; deploys as S-05 without a token | Compose older than 2.24 rejects `required: false` |
| 2. Cloudflare and VPS Bootstrap | Domain, zone, certificate check, tunnel, env files | A misconfigured zone issues a certificate naming the label |
| 3. Public Address Go-Live | End-to-end HTTPS use, CT, listener, attempt-bucket, memory, and deploy-independence checks | Subnet overlap on the VPS, or SSE buffering at the edge |

**Prerequisites:** S-05 (`deployment-manual-deploy`) done. Phases 2–3 need a purchased domain and a Cloudflare account.

**Estimated effort:** Phase 1 about half a day. Phases 2–3 about an evening, excluding domain propagation.

## Open Risks & Assumptions

- Passive DNS datasets may record the label once clients resolve it, and nothing fully prevents that.
- Cloudflare's CT-monitoring emails ignore certificates Cloudflare issues itself, so the crt.sh check is the only guard against an unexpected certificate naming the label.
- Mikrus LXC may throttle QUIC. The runbook falls back to `TUNNEL_TRANSPORT_PROTOCOL=http2`.
- `172.30.238.0/24` is assumed free on the VPS, and Phase 2 checks it.

## Success Criteria (Summary)

- The TUI signs in and streams a capture reply over `https://<label>.<domain>`, and crt.sh shows no certificate naming the label.
- The VPS opens no new port, and attempt limits separate client networks.
- A deploy without a tunnel, or with a broken one, still switches the API green.
