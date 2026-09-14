# Capture and Distill Separation — Plan Brief

> Full plan: `plan.md`

## What & Why

Every capture session, note, topic, tag, and card becomes the property of the person who signed in when it was created. Anything reachable from HTTP refuses another person's data. Cards generated in the background inherit the owner from the approved note (AC-15), which makes this slice the capture and distill half of FR-008.

## Starting Point

S-01's gate already yields a `UserId`, but no route or handler uses it. No capture or distill aggregate, port, envelope, or table carries an owner. Vocabulary matching and the notes queries span the whole instance.

## Desired End State

- Another person's capture session, note, or cards answer the same 404 as an unknown id.
- `GET /notes` lists only the caller's notes.
- Topic and tag reuse only ever matches the drafting person's own vocabulary.
- A note approved by a person yields cards stamped with that person.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Capture and distill together | One slice, ownership crosses the outbox | Cards are generated in the background from a person's notes | Roadmap |
| Remember | Still global until S-05 | The hosted instance stays private until FR-008 holds | Roadmap |
| Topic/tag vocabulary | Per person | A shared vocabulary would leak another person's topic labels | Plan |
| Foreign id response | Same not-found as an unknown id | Existence is not confirmed, and no new codes are needed | Plan |
| Enforcement by id | Handler compares `aggregate.owner_id` | The user's choice: ports stay keyed by id | Plan |
| Collective reads and queries | Port takes `UserId` and filters at the source | CQRS-lite queries have no aggregate or handler to check in | Plan |
| Card ownership | Own `owner_id`, stamped from the note | Checks need no second read, and S-05's catalog filters without a join | Plan |
| Schema | `owner_id NOT NULL`, no backfill, two chained revisions | The schema enforces ownership, and every instance starts empty | Plan / PRD |
| `list_all` | Left unscoped | Only adapter callers use it, and S-05 replaces the remember one | Research |
| Isolation proof | Contract cases plus two-person HTTP tests | The router forgetting to pass the person is the likeliest slip | Plan |

## Scope

**In scope:**
- Owner on capture sessions, capture notes, topics, tags, distill notes, and cards.
- `owner_id` on `note_approved`.
- Owner-filtered `nearest` and notes queries.
- Foreign-session not-found in capture commands.
- Two Alembic revisions.
- Contract cases on both adapters.
- HTTP two-person tests.

**Out of scope:**
- Remember catalog, locator, sittings, lock, and card rejection ownership (S-05).
- TUI.
- Backfill.
- New exception codes.
- BDD scenarios, which come from `/bdd`.

## Architecture / Approach

```
require_sign_in ─► UserId ─► capture routes ─► commands (compare session.owner_id)
                                  │
                   CaptureSession.owner_id ─► Note / Topic / Tag
                                  │
                  note_approved{owner_id} ─► SaveNote ─► distill Note ─► Card.owner_id
                                                                   │
                         notes routes ─► query ports(owner) ─► WHERE owner_id = owner
```

Each context is a stubs-then-behavior pair:
- The stubs phase threads the owner everywhere and stamps it on creation, but excludes nothing.
- The behavior phase adds the exclusions behind tests written first.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Capture ownership symbols | Fields, signatures, capture revision, routes, stable fixture identity | Wide signature churn across existing capture tests |
| 2. Capture separation | Per-person vocabulary, foreign-session 404 | Closed-session check leaking existence if ordered first |
| 3. Distill ownership symbols | Owner across the outbox onto notes and cards, distill revision | Remember tests building distill objects without an owner |
| 4. Distill separation | Owner-filtered notes queries, two-person chain proof | Composing capture and distill on one outbox in the test |

**Prerequisites:**
- `TEST_DATABASE_URL` for the Postgres lane.
- An emptied dev database before `alembic upgrade head`.

**Estimated effort:** 4 phases, roughly 2 sessions of `/implement` → `/unit-test` → `/implement`.

## Open Risks & Assumptions

- Remember still reads every person's cards until S-05. This is accepted because the hosted instance is not public.
- The untracked property tests under `backend/tests/property/` may build distill objects and need an owner in their factories.
- The uncommitted `backend/src/adapters/compose.py` edit is left out of every commit of this change.

## Success Criteria (Summary)

- The backend suite (both lanes) and basedpyright are green.
- Person B gets 404 on person A's session, note, and cards, and an empty notes list.
- Cards generated from A's approved note carry A as their owner.
