## Context

Weles is a solo personal-knowledge tool built around one loop — capture, distill, remember (see `context/foundation/project-overview.md`) — not a team product. Two things needed cementing at once, because they turned out to force each other: the shape of the repository, and the core stack. The stated constraint — a CLI that can be built "without backend code in the binary" — is a statement about a compiled artifact, which makes the stack choice a repo-shape decision, not a separate one.

The backend carries the heavy lifting: LLM integration for the distill step (targeting `pydantic-ai`), semantic search over notes, and spaced-repetition scheduling. The TUI is meant to be maximally thin — a presentation layer, not a place where business logic accumulates. The author has React fluency and anticipates other visual adapters later (a web app, a React Native mobile client), and wants the option to carry over TUI mental model and component patterns to those rather than starting from zero. Authentication is required from the MVP, which matters here even though the mechanism itself is deferred to a later decision: it means the backend is designed as a proper API surface from day one, not an implicitly-trusted local-only process.

## Decision

The repository is a single monorepo containing, at minimum, two top-level packages with no shared business-logic code between them:

- A **TUI client**, in Node.js using Ink (React for CLIs).
- A **backend service**, in Python, built around `pydantic-ai` for LLM integration.

The backend runs as a persistent daemon exposing an authenticated HTTP API. The TUI — and any future client (web, mobile) — talks to it purely as an API client; no backend logic is compiled or bundled into the TUI artifact. Because Node and Python cannot share code in-process, this boundary is enforced by the choice of stack itself, not by import discipline or code review.

The authentication mechanism is explicitly out of scope for this decision; only the requirement — auth present from MVP — is settled here.

## Consequences

- Two runtimes and dependency ecosystems (Node/npm, Python/uv or venv) means two sets of tooling, linting, and CI to maintain — accepted in exchange for the best-fit framework per surface: Ink for the TUI given the author's React fluency and the intent to reuse that mental model for future web/mobile adapters, `pydantic-ai` for the LLM-heavy backend where the Python ecosystem is meaningfully more mature than Go or Rust equivalents.
- The backend's lifecycle now needs active management — something has to start and supervise the daemon (a process manager, a systemd/launchd unit, or the TUI spawning it on first run). This detail is not decided here.
- The HTTP API becomes the backend's sole entry point for any client, so its contract is a first-class artifact from the start rather than an internal implementation detail — versioning and stability of that contract will need its own attention as more clients arrive.
- The cross-language split removes the main weakness a same-language monorepo would have had: there is no in-process shortcut available even under time pressure, so "the TUI stays thin" is guaranteed by the stack rather than needing ongoing enforcement.
- Requiring auth from MVP means the daemon cannot later be treated as an implicitly-trusted loopback-only process without revisiting this decision — worth keeping in mind when the auth mechanism itself is chosen.
- A subprocess-per-call model (TUI exec'ing the backend per operation) is effectively foreclosed by this stack: Python's interpreter and import cold-start cost (`pydantic-ai`, embedding libraries) would tax every keystroke-driven TUI interaction. The daemon absorbs that cost once, at startup, instead.

## Alternatives Considered

1. **Single-language, compiled stack (Go or Rust)**, with TUI and backend as separate binaries/modules in one workspace. This was the initial recommendation going into the session — it gives the strongest possible compile-time guarantee that backend code cannot end up in the TUI binary. Rejected because neither ecosystem has an LLM/embeddings story approaching `pydantic-ai`'s maturity, and deep LLM integration is the backend's central concern.
2. **Python end-to-end**, using Textual instead of Ink for the TUI, avoiding a second runtime entirely. A genuinely strong alternative: it keeps the same process-boundary guarantee without any cross-language complexity, and Textual is a mature, capable TUI framework. Rejected because the author's React fluency and the intent to carry the TUI's component/mental model over to a future web app or React Native mobile client is a reuse path Textual does not offer.
3. **Subprocess-per-call** instead of a daemon (the TUI exec's the backend binary per operation, git-porcelain style). Rejected on cold-start grounds: Python's per-invocation interpreter and import cost is too high for a TUI that needs to feel responsive to individual keystrokes or fast navigation, and it would reopen the local data store on every call instead of holding it open across a session.
4. **Polyrepo** (separate repositories for TUI and backend). Rejected: it doubles repository, CI, and versioning overhead for a solo project, and works against the priority of shipping vertical slices quickly. The boundary-enforcement benefit polyrepo would normally buy is largely moot here anyway, since Node and Python cannot share code regardless of repository layout.
