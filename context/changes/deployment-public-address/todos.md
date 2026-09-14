---
change_id: deployment-public-address
current_phase: 1
next_step: 1.1
next_command: /implement deployment-public-address phase 1
updated: 2026-09-14
---

### Phase 1: Tunnel Sidecar in the Stack

#### Automated

- [ ] 1.1 Compose cloudflared is pinned, profiled, exec-healthchecked, portless, and fixed on edge
- [ ] 1.2 Compose api joins default and edge, and cloudflared's env file is optional
- [ ] 1.3 Shellcheck reports no findings on remote-deploy.sh
- [ ] 1.4 remote-deploy.sh waits on api alone and starts cloudflared only with its env file
- [ ] 1.5 Repository contains no tunnel identifier or token value
- [ ] 1.6 README has a Public address subsection naming no instance

#### Manual

- [ ] 1.7 Compose on the VPS reports version 2.24 or newer
- [ ] 1.8 A deploy without cloudflared.env ends green with no cloudflared container

### Phase 2: Cloudflare and VPS Bootstrap

#### Manual

- [ ] 2.1 Domain uses Cloudflare nameservers with DNSSEC signatures
- [ ] 2.2 Edge certificates list only the apex and its wildcard, with Total TLS off
- [ ] 2.3 Tunnel public hostname is a first-level random label routed to api:8000
- [ ] 2.4 Both env files are mode 600 and backend.env trusts the sidecar address
- [ ] 2.5 No existing Docker network overlaps the edge subnet

### Phase 3: Public Address Go-Live

#### Manual

- [ ] 3.1 A gated deploy ends green with api, postgres, and cloudflared healthy
- [ ] 3.2 TUI at the public HTTPS address signs in and streams a capture reply
- [ ] 3.3 crt.sh lists no certificate naming the instance label
- [ ] 3.4 The VPS listens on no new port
- [ ] 3.5 Sign-in failures from one network do not lock out another
- [ ] 3.6 Memory snapshot with the tunnel running is recorded
- [ ] 3.7 A deploy with a broken tunnel token still switches the API green
