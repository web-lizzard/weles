## Current State

Weles is a personal second-brain tool built around **capture → distill → remember** (per `context/foundation/project-overview.md`, held loosely as product framing — not yet SoT). This session is the first pass at the technical shape underneath that loop.

**Stack direction (provisional):** Python for the API, Node for a TUI client, both living in this repo as a monorepo.

**Deployment constraint:** starts on a cheap VPS — no broker, no multi-process fan-out. This pushes toward async tasks in a single event loop rather than distributed workers.

**Loop/worker split — settling shape:**
1. Main loop — conversational entry point, API is the input surface. A general command dispatcher: a "capture" path (think out loud → note) and a "remember" path (a command that opens a review session with flashcards on a given topic) both live here.
2. Capture path, concretely: user converses with the agent about some topic → at session end the agent drafts a note plus tags (tags are picked from an existing DB-backed vocabulary first, new ones are only minted and shown to the user when nothing fits) → user approves → payload goes to the outbox as an envelope.
3. Note-save worker — persists the approved note (+ tags) to storage, consuming from the outbox.
4. Flashcard-gen worker — derives flashcards from a saved note (the "distill" step).
5. "Remember" has no separate worker — it's a main-loop command, not an async job, since it's a synchronous read/review flow rather than background processing.

**Storage:** Postgres. One outbox table, envelope carries a `type` field so note-save and flashcard-gen filter/consume from the same table.

**Semantic linking:** embeddings live at the *session* level — each session carries a topic/tag, and that topic/tag is what gets embedded, not raw note or flashcard content. Flashcards link to each other across time transitively, through their parent session's topic embedding, rather than each card getting its own vector. Still open: who assigns a session's topic/tag (main loop via LLM extraction, or the user by hand), and which worker/step owns computing the embedding once the tag exists.

**App-wide policy:** the agent never acts without user approval — this is the general rule, not something specific to note drafts. The tags/note draft approval is one instance of it.

**Flashcard-gen, concretely:** triggered off a note already saved in the DB (post note-save, not straight from the live conversation) → agent generates flashcards and saves them to the DB → user reviews and can reject afterward. This is a deliberate, accepted exception to the approval-policy: flashcards live in their own table (rejection can't pollute notes), and a rejected flashcard is soft-deleted, not purged — kept as a negative signal so the agent doesn't regenerate a near-duplicate later.

**Scope guard (explicit from user):** this session stayed at the shape/organizing level — not implementation detail. Session closed here; the shape below is a snapshot to resume from, not a settled design.

**Remaining open threads, for next session:**
- Stack pick (Python API + Node TUI monorepo) and single-loop-on-cheap-VPS are both still provisional working assumptions, never revisited after being raised.
- Outbox: table+envelope shape is settled (one Postgres table, `type` field), but whether the main loop is a pure producer or also a consumer of it is unresolved.
- Semantic linking: embedding target is settled (session topic/tag), but who computes it and at which step is unresolved.
- Storage schema, and "remember" review-session mechanics, were flagged as candidate next topics but not opened this session.

## Log

### 2026-08-28 — stack-split: Python API + Node TUI, single monorepo — OPEN
Why: user's provisional stack pick — Python for the API, Node for the TUI — both housed in this repo as one monorepo rather than split repos. Not yet justified beyond "probably," treated as a working assumption.

### 2026-08-28 — single-loop-workers: async tasks in one event loop, cheap VPS — OPEN
Why: deployment starts on a cheap VPS, which rules out a broker or multi-process worker fleet at this stage. Async tasks cooperating in a single loop is the fallback shape that fits that budget constraint.

### 2026-08-28 — worker-topology: three roles — main loop, note-save, flashcard-gen — OPEN
Why: user named three candidate loop participants — a main loop taking conversational API input, a worker that saves a note to storage, and a worker that generates flashcards from a note. Maps loosely onto the product's capture/distill split, but the mapping itself hasn't been confirmed yet.

### 2026-08-28 — outbox-envelope: thin outbox with envelope feeds both workers — OPEN
Why: user wants a lightweight outbox pattern (envelope-wrapped work items) so the note-save and flashcard-gen workers consume from a queue-like structure rather than being invoked inline by the main loop. Shape (one outbox vs. two, main loop's relation to it) not yet settled.

### 2026-08-28 — outbox-envelope: one Postgres table, envelope `type` field — ACCEPTED
Why: user settled the shape — a single outbox table in Postgres, with the envelope's `type` field letting note-save and flashcard-gen each filter their own work items. Keeps infra to the one Postgres instance the cheap-VPS constraint already implies, rather than two queues or a broker.
Supersedes: 2026-08-28 outbox-envelope (OPEN) — the "one vs. two outboxes" question is resolved; "main loop's relation to it" (pure producer vs. also consumer) is still open.

### 2026-08-28 — remember-command: remember is a main-loop command, not a worker — ACCEPTED
Why: user resolved the earlier open question about where "remember" lives — it's a synchronous command inside the main loop that opens a review session with flashcards on a given topic, not a background job behind the outbox. Reframes "main loop" from capture-only entry point to general command dispatcher (capture path + remember path).

### 2026-08-28 — semantic-linking: embeddings to connect flashcards across time — OPEN
Why: user flagged that flashcards need embeddings so cards on the same topic from different periods can be linked semantically, not just accumulate as disconnected items. Extends the product overview's "searchable by meaning" idea (currently framed around notes) to flashcards specifically. Left open: computed on notes vs. flashcards vs. both, which worker owns the computation, and storage (pgvector on the same Postgres instance is the implied default given the single-DB direction).

### 2026-08-28 — semantic-linking: embedding target is session topic/tag, not note/flashcard content — ACCEPTED
Why: user clarified the earlier open question — the embedding isn't computed per-note or per-flashcard, it's computed on a session's topic/tag. Sessions (and their flashcards) link to each other transitively through that shared topic-embedding space. Narrower and cheaper than embedding every note/flashcard individually.
Supersedes: 2026-08-28 semantic-linking (OPEN) — "notes vs. flashcards" question is moot now; new open question is who assigns a session's topic/tag (LLM extraction in the main loop, or manual) and which step computes the embedding once the tag exists.

### 2026-08-28 — capture-flow: draft → approve → outbox, tags picked from existing vocabulary first — ACCEPTED
Why: user laid out the concrete capture flow. The agent drafts both the note and its tags at session end, choosing from a DB-backed tag vocabulary before minting new ones (new tags are shown to the user rather than silently created). The user then approves, and only then does the payload go to the outbox. This answers the "who assigns the tag" open question from the semantic-linking thread: the agent does, with a controlled vocabulary and a human approval gate — not free-form per-session tagging.
Consequence: a controlled, reused tag vocabulary makes the session-level embedding idea (see semantic-linking) more robust — fewer near-duplicate tags to embed and compare.

### 2026-08-28 — approval-policy: agent never acts without user approval, app-wide — ACCEPTED
Why: user generalized the tag-editing question into a blanket rule: nothing the agent produces is committed without the user approving it first. Resolves the earlier open question (can the user edit/reject proposed tags) — yes, as one case of this wider policy — and sets a constraint every future worker/flow in this session should be checked against.

### 2026-08-28 — flashcard-gen-flow: generated from a saved note, agent creates + saves, user reviews/rejects after — OPEN
Why: user described flashcard-gen as reading a note already committed to the DB, then the agent both creates and saves the flashcards, with the user reviewing and able to reject afterward. Flagged as in tension with the just-stated approval-policy (act-then-review vs. the "nothing without approval" rule used for notes/tags) — not yet resolved whether this is an intentional exception or needs to move to an approve-before-persist shape.

### 2026-08-28 — flashcard-gen-flow: act-then-review confirmed as an intentional exception — ACCEPTED
Why: user accepted the tension as a deliberate exception rather than a gap — low-stakes because flashcards sit in their own table (a rejection can't corrupt note data), and rejected flashcards are kept (soft-deleted, not purged) specifically so the agent can check past rejections and avoid regenerating a near-duplicate card later.
Supersedes: 2026-08-28 flashcard-gen-flow (OPEN) — the approve-before-persist question is settled: notes/tags require pre-approval, flashcards deliberately don't.
