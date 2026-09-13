---
date: 2026-09-13T14:20:00+02:00
topic: "Authentication patterns for a public TUI with a deployed backend and a small user whitelist"
topic_slug: null
container_id: auth-flow
tags: [research, auth, tui, backend, whitelist]
last_updated: 2026-09-13
---

# Research: Authentication patterns for a public TUI with a deployed backend and a small user whitelist

## Research Question

/research auth-flow przeszukaj sieć, dobre wzorce uwierzytelniania dla aplikacji tui:

use case
1. aplikacja publiczna (github registry)
2. backend deployowany wymagan tożsamość/konto bez tego capture/distill/remember flow nie działa
3. najlepiej jakaś whitelista uzytkownikow,  obecnie jedno konto, drugie moze byc recenzenta, bo aplikacja jest dowodem na certyfikat (konkretnie uzyskanie go)

## Summary

A **public TUI** distributed via GitHub must be treated as an OAuth **public client** (no embedded `client_secret`). The recommended shape is: the CLI authenticates the human (device flow and/or authorization code with PKCE on loopback), the **deployed backend** validates identity against an **allowlist** and issues **Weles API tokens**; every capture/distill/remember request fails closed without a valid credential. For a certificate demo with one owner and one reviewer, start with GitHub-backed login plus server-side allowlist and optional per-user API keys for the reviewer; store TUI tokens in the OS keychain with short-lived access tokens and refresh rotation. Edge-only auth (Cloudflare Access, Google IAP) can reduce login UX work but the FastAPI layer must still validate JWTs or equivalent so tenancy and data isolation stay enforceable in application code.

## Findings

### Repository baseline

- The `auth-flow` effort exists but has no PRD yet; architectural intent already requires an authenticated HTTP API from MVP (`context/adrs/repo-shape/decision.md`).
- The backend mounts capture, notes, and remember routers with **no auth middleware** (`backend/src/main.py:36–43`); HTTP dependencies inject commands only, not identity (`backend/src/adapters/http/capture.py`, `backend/src/adapters/http/remember.py`).
- The TUI OpenAPI client targets the backend with **no `Authorization` header** (`tui/src/api/client.ts:27–30`).
- Domain “sessions” are capture sessions and review sittings, not login sessions; data is globally visible today (e.g. remember `ReviewCatalog` loads all notes — `backend/src/adapters/out/in_memory/remember/review_catalog.py:22–38`).
- Future auth must scope the full chain capture → distill → remember under one tenancy key; partial `user_id` on one port is worse than none (`context/archive/changes/2026-09-10-remember-flow-session-resume/frame-log.md`).
- Product positioning is single-person, not multi-tenant teams (`context/foundation/project-overview.md`), which aligns with a **small allowlist** rather than full SaaS identity.

### Public CLI/TUI → deployed API (web patterns)

- **Public clients** cannot safely ship OAuth client secrets; RFC 8628 treats device clients as public; RFC 8252 requires native apps to register as public clients unless using per-instance secrets.
- **Primary TUI login:** hybrid **OAuth 2.0 Device Authorization Grant (RFC 8628)** for headless/SSH and **authorization code + PKCE (S256) + loopback (RFC 8252)** when a local browser is available. RFC 8628 is not intended to replace browser OAuth on capable devices—use both in one binary where possible.
- **GitHub as IdP:** enable device flow on a GitHub OAuth app or prefer a **GitHub App** (finer permissions, short-lived tokens). CLI tutorials explicitly recommend device flow for headless tools. Exchange the GitHub token **on the backend** for a **Weles session/JWT** so the TUI does not send broad GitHub tokens on every API call.
- **Token storage:** prefer OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service); avoid long-lived plaintext files and local env vars for interactive use; use refresh token rotation where supported.
- **Avoid as primary:** embedded secrets, long-lived PATs in config for all users, trusting only edge proxy auth without origin validation.

### Whitelist and small-team identity (web patterns)

- **Allowlist models:** static emails or GitHub logins in server config; Clerk dashboard users; Cloudflare Access **Email** selectors; GCP IAP IAM bindings to `user:email`.
- **Magic link + allowlist in-app** is a moderate-code path with good reviewer UX (SMTP, one-time tokens, enumeration-safe responses).
- **Managed Clerk Hobby** offers magic link and email codes with low ops; suitable when avoiding custom auth code.
- **Two API keys** (owner + reviewer) are the lowest ops for a certificate demo but are weak end-user auth per OWASP; acceptable as a documented secondary path (`--api-key`) with rotation after review.
- **Fail closed:** middleware rejects missing/invalid credentials on all protected routes; JWT validation must check signature, `iss`, `aud`, and expiry; Cloudflare Access requires validating `Cf-Access-Jwt-Assertion` at the origin, not only at the edge.
- **Self-hosted IdPs** (Authentik, Zitadel VM) are disproportionate for two humans unless the certificate narrative includes running that stack.

### Recommended phased approach for Weles

**Phase A (MVP auth + certificate reviewer):**

1. Require `Authorization: Bearer` on all capture, notes, and remember HTTP routes.
2. Maintain an **allowlist** of two principals (e.g. GitHub login or email) in deployment config/secrets.
3. TUI: GitHub **device flow** (with PKCE+loopback when available) → backend token exchange → store **Weles** access/refresh tokens in keychain.
4. Optional **reviewer API key** header for users without GitHub, documented and rotatable.

**Phase B:** replace custom token issuance with Clerk or magic-link allowlist if maintenance cost grows.

**Not recommended initially:** edge-only protection without FastAPI JWT/session validation tied to a tenancy key in persistence ports.

## Code References

- `context/adrs/repo-shape/decision.md:5–6, 14–16, 24` — backend is a daemon with authenticated HTTP API; auth required from MVP
- `context/foundation/project-overview.md:21–25` — single-person product scope
- `context/efforts/auth-flow/effort.md:1–12` — effort shell; Goal not yet filled via PRD
- `backend/src/main.py:36–43` — FastAPI app without auth middleware
- `backend/src/adapters/http/capture.py:39–70` — unauthenticated capture endpoints
- `backend/src/adapters/http/remember.py:39–95` — unauthenticated remember endpoints
- `tui/src/api/client.ts:27–30` — HTTP client without Authorization
- `backend/src/adapters/out/in_memory/remember/review_catalog.py:22–38` — global note/card catalog, no owner filter
- `context/archive/changes/2026-09-10-remember-flow-session-resume/frame-log.md:68–72, 110–118` — tenancy axis and risk of partial user scoping

## External References

- https://datatracker.ietf.org/doc/html/rfc8628 — OAuth 2.0 Device Authorization Grant; public clients, no redirect URI, polling model
- https://datatracker.ietf.org/doc/html/rfc8252 — OAuth 2.0 for native apps; loopback redirects, PKCE requirement for public clients
- https://datatracker.ietf.org/doc/html/rfc9700 — OAuth 2.0 security BCP; public clients must use PKCE
- https://oauth.net/2/device-flow/ — device flow summary and grant type URN
- https://oauth.net/2/pkce/ — PKCE recommended for all clients; use S256
- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow — GitHub device flow endpoints and enablement
- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/differences-between-github-apps-and-oauth-apps — GitHub App vs OAuth app; fine-grained permissions and short-lived tokens
- https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/building-a-cli-with-a-github-app — CLI should use device flow; token file permissions
- https://auth0.com/docs/get-started/authentication-and-authorization-flow/device-authorization-flow — device flow for input-constrained clients
- https://auth0.com/docs/secure/security-guidance/data-security/token-storage — store tokens in OS secure storage
- https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation — refresh rotation on each use
- https://blog.logto.io/cli-authentication-methods — keychain vs env vars for CLI credentials
- https://www.heroku.com/blog/securing-heroku-cli-credentials-with-system-keychain-storage/ — default keychain storage pattern
- https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/ — API keys are not end-user authentication
- https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html — validate iss, aud, exp, signature
- https://pypi.org/project/maglink/ — Python magic-link helper for small allowlists
- https://github.com/magic-link-sso/magic-sso — DIY magic link SSO with allowed emails
- https://clerk.com/pricing — Clerk Hobby magic link / email codes and MRU limits
- https://developers.cloudflare.com/cloudflare-one/policies/access/ — Access Allow policies (email selectors)
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/ — validate Access JWT at origin
- https://docs.cloud.google.com/iap/docs/managing-access — IAP IAM bindings per user
- https://selfhosting.sh/compare/zitadel-vs-authentik/ — ops cost of self-hosted IdPs for tiny user sets

## Open Questions

- Where is the backend deployed (Mikrus, GCP, Cloudflare Tunnel)—does edge auth (Access/IAP) already exist?
- Must the certificate reviewer use GitHub, or is a one-time API key acceptable in the submission narrative?
- Should the allowlist key be GitHub `login`, verified email, or an internal `user_id` minted on first login?
- When Postgres lands (`db-adapter`), which persistence ports get the tenancy column first without leaving global leaks in remember/catalog queries?
