## Current State

Session closed. Everything settled lives in `frame.md`'s body; nothing below is a requirement.

Two items handed to whoever picks this up next:

- **No product-level driver for the AC-19/AC-20 condition.** Neither a note edit nor a note delete exists anywhere in the stack, so a stored quote cannot stop resolving through any user action. A scenario covering the unfindable source must construct that state through an adapter or fixture rather than through the app. See `unreachable-condition`.
- **The divergence from the browse path is intentional.** distill still reaches the note without a highlight and says "Source fragment was not found in this note."; the review will do neither. Read `browse-review-asymmetry` before filing it as an inconsistency.

Both are notes for `/discover-contracts`, `/plan` and `/bdd`, not open argument.

## Log

### 2026-09-11 — source-jump-in-review: session opened on stated framing — OPEN

The change was materialized from effort `remember-flow` slice S-05 against AC-18/19/20 (`context/efforts/remember-flow/stories.md:97-112`). A `/research` pass already established the anchor surface end-to-end in distill (`context/changes/remember-flow-source-jump/research.md`). Framing opens with the user's design position stated as one sentence; the job of this session is to split what must be true from how it appears.

**Why:** The stated framing is a UI shape, not a requirement set. AC-18–20 say only *reach the fragment* and *never withhold a card whose fragment is gone*. Everything else in the sentence — back-gating, Esc, a full note screen — is a candidate decision that has to survive argument before it enters the body.

### 2026-09-11 — back-gated-source: source is unreachable until the back is revealed — ACCEPTED

**Why:** Not a UI nicety but a leak. The only wired generator sets a proposal's `quote` to the full raw block text of the note (`backend/src/adapters/out/in_memory/distill/card_generation.py:38-45`), and grounding requires the quote to be a verbatim substring of a block (`backend/src/domain/distill/note_document.py:46-85`), so a card's source passage reliably contains the answer the back states. A route to it before the back is revealed would grade the user's recall against text they had just been shown.

**Consequence:** The availability of the route is a function of sitting phase, not only of the card. A card whose fragment resolves is still sourceless while its back is hidden.

### 2026-09-11 — source-view-is-a-dead-end: the source view offers no navigation onward — ACCEPTED

**Why:** distill's `NoteDetailScreen` is a navigable surface with a tab strip into the card list and its own jump wiring (`tui/src/screens/NoteDetailScreen.tsx:23-40`, `tui/src/components/NoteTabStrip.tsx`). Reusing that surface inside a sitting gives a reviewer a side exit out of the review, which undercuts the effort's premise that everything due can be worked through in one sitting (`context/efforts/remember-flow/effort.md`, Goal). The source view is a read-only excursion with exactly one way out.

**Consequence:** The browse-path note screen cannot simply be mounted inside the sitting; what the review needs is note content plus a marked span, which is narrower than what that screen offers.

### 2026-09-11 — contextual-esc: Esc closes the innermost open view — ACCEPTED

**Why:** `SittingOverlay` currently binds Esc unconditionally to closing the sitting overlay and resetting the sitting store (`tui/src/screens/SittingOverlay.tsx:41-45`). Introducing a view above the card without touching that binding would make the source view's natural exit gesture abandon the review instead — a far more costly outcome than the one the user intended, and one that collides with AC-21's promise that stepping into a review and back out is free.

**Consequence:** Abandoning a sitting from an open source view takes two gestures. The body states the invariant; the key binding itself is plan-level work.

### 2026-09-11 — missing-fragment-behaviour: jump still reaches the note without a highlight — REJECTED

**Why:** The user's first position was that losing the fragment should cost the highlight, not the route — arguing that a note without a marked span still recovers an ambiguous card. That is a defensible product position, but it contradicts the effort's acceptance authority verbatim: FR-016 reads "only the jump to it becomes unavailable" (`context/efforts/remember-flow/prd.md:65`) and AC-20 reads "the jump to its source becomes unavailable, rather than the card being withheld" (`context/efforts/remember-flow/stories.md:110`). A change cannot restate an AC into its opposite; amending it is an effort-level act. Put the choice — amend AC-20 or comply — to the user, who chose to comply.

**Consequence:** When the fragment cannot be found the route is absent, not degraded. The user reaches nothing. Whether that silence is itself acceptable is still an open thread.

### 2026-09-11 — staleness-window: when the route's availability is decided — REJECTED

**Why:** Raised as a possible body statement — does the affordance describe the note at the moment of asking or at the moment the card was served? Grounded and dropped: the product exposes no way to change a note at all. The notes router carries only `GET /notes/{note_id}` and `GET /notes/{note_id}/cards` (`backend/src/adapters/http/notes.py:32-45`), and the TUI client has no update call. There is no window for a note to drift during a sitting, so a rule about freshness would be a rule about nothing.

**Consequence:** The body says nothing about staleness, and the out-of-scope boundary says so explicitly rather than leaving the silence ambiguous for `/plan`.

### 2026-09-11 — deleted-note-vs-moved-quote: one condition, not two — ACCEPTED

**Why:** From the card's side both collapse to the same fact — the source cannot be reached — and AC-20 prescribes one behaviour for that fact. Splitting them would put a distinction in the body that no requirement consumes. Reinforced by the same evidence as `staleness-window`: no delete route exists either, so the second branch would be entirely hypothetical.

### 2026-09-11 — silence-on-absence: the missing route is not announced — ACCEPTED

**Why:** A sitting exists for one act — grading recall — and a notice about notes drifting away from cards competes with it while being actionable nowhere in that screen. The absence of the affordance is itself the signal. Recorded as an explicit out-of-scope statement rather than an omission, so a later change can own the reporting without reopening this one.

### 2026-09-11 — unreachable-condition: AC-19/20 describe a state the product cannot produce — OPEN

**Why:** Established while grounding `staleness-window`. With no note edit and no note delete anywhere in the stack, a card's stored quote cannot stop resolving through any user action. The requirements are still correct — they guard a future in which notes become editable — but nothing that exercises them can go through the product's own surface. A scenario must construct an unresolvable card through an adapter or fixture, and `/plan` should expect that seam rather than discover it.

### 2026-09-11 — browse-review-asymmetry: the two flows answer a missing fragment differently, on purpose — ACCEPTED

**Why:** distill's browse path already implements the option rejected for review: on an unresolved anchor it still renders the note, omits the highlight, and states "Source fragment was not found in this note." (`tui/src/screens/NoteDetailScreen.tsx:98-100`). After this change the same card and the same note produce different behaviour depending on where the user came from. Kept, because the modes differ in what the user is doing: browsing is examining one's own notes, where the drift is the interesting fact; a sitting is grading recall, where it is a distraction from the only act available on that screen. Recorded explicitly so the divergence reads as a decision and not as an oversight in a later review.

**Consequence:** The review's source view cannot be the browse screen with navigation disabled — the two now disagree about what a missing fragment means, on top of disagreeing about navigation.

### 2026-09-11 — source-view-extent: fragment in context, expandable to the whole note — ACCEPTED

**Why:** The browse path shows the anchored block and everything after it, filtering out every earlier block (`tui/src/screens/NoteDetailScreen.tsx:55-62`). That is the wrong half to keep: the text leading up to a fragment is usually what disambiguates it. The review's source view therefore shows the marked fragment with note text on both sides, and offers the note in full for the case where that is not enough.

**Consequence:** Expansion is a second state of one view, not a destination, so the dead-end boundary survives it: the expanded state is equally read-only and exits to the card by the same gesture. Esc is thereby held to exactly one level of nesting inside a sitting — it never has to mean "back to the smaller view".

### 2026-09-11 — visit-leaves-no-trace: reading the source is unobservable — ACCEPTED

**Why:** Confirmed by the user and by the model. `Sitting` is a frozen aggregate of `card_ids` plus snapshotted timestamps and limits (`backend/src/domain/remember/sitting.py:26-33`), and `ReviewEvent` carries `card_id`, `reviewed_at`, `outcome`, `sitting_id` (`backend/src/domain/remember/review_event.py:8-12`). There is no field a source visit could occupy; recording one would mean a new domain event and an outbox dump for a fact nothing consumes. Stated as a requirement rather than left as an absence, so a later change adding review telemetry knows it is reversing a decision.
