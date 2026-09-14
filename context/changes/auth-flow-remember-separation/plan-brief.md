# Remember Separation — Plan Brief

> Full plan: `plan.md`

## What & Why

S-04 separated captures, notes, and cards per person. Remember still offers every person's cards, resumes the newest sitting on the instance, and accepts any sitting id. This change closes separation across the whole chain (AC-14, AC-16, AC-17), and stops two people from serializing each other's reviews.

## Starting Point

Distill cards carry `owner_id`, and routes receive the gate's `UserId`. Remember's catalog, source locator, `latest()`, and sitting-loading handlers ignore ownership. All remember mutations share one global advisory lock.

## Desired End State

A person's due count, sittings, grades, and rejections involve only their own cards. Another person's sitting answers `404 sitting_not_found` everywhere. Two people can review at the same time. `remember_sittings.owner_id` is `NOT NULL`.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Where ownership is enforced | Handler compares `sitting.owner_id`; ports filter by owner argument | Same split S-04 used; no ambient current-user reader | Research / Plan |
| Foreign sitting response | Existing `404 sitting_not_found`, checked before expiry | A foreign id must not reveal existence | Plan |
| Lock grain | Per person: `pg_advisory_xact_lock(namespace, hashtext(owner))`, per-owner `asyncio.Lock` | Keeps the open-sitting race guard, which is per person once `latest` is, without cross-person blocking | Research / Plan |
| Owner columns | Only `remember_sittings` | Events and scheduling states are reachable only via an owned sitting or the caller's catalog | Plan |
| `card_rejected` owner | Not added | A sitting only holds the caller's cards, so rejection cannot target a foreign card | Plan |
| Chain proof | One in-memory HTTP test, capture → distill → remember, two people | Request-to-response evidence, mirroring S-04 Phase 4 | Plan |

## Scope

**In scope:**
- Sitting owner.
- Owner-scoped catalog, locator, and `latest`.
- Ownership checks in five handlers.
- Per-person lock.
- One Alembic revision.
- Route wiring.
- A chain separation test.

**Out of scope:**
- Owner on events, scheduling states, and `card_rejected`.
- Lock redesign beyond grain.
- Queries under the lock.
- TUI changes.
- BDD scenarios (`/bdd`).
- The uncommitted `compose.py` LLM-provider edit.

## Architecture / Approach

The gate's `UserId` enters at the remember router and is passed as `owner` into every handler. It then reaches the unit-of-work factory (which keys the lock), the catalog and locator (which filter distill cards), and `latest` (which filters sittings). Handlers that load a sitting by id compare its owner and raise not found. One stubs phase lands all symbols with ownership ignored. Three behavior phases add exclusions behind tests.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Remember ownership symbols | Signatures, column, migration, route wiring; fixtures seed the gate's person | Missed fixture seeding turns Phase 2 red for unrelated reasons |
| 2. Remember read scoping | Catalog, locator, `latest` filter by owner on both adapters | In-memory catalog filtering diverging from SQL |
| 3. Sitting ownership and chain separation | Foreign sitting → 404 in five handlers; two-person HTTP chain test | Check placed after expiry leaks existence via 409 |
| 4. Per-person remember lock | Lock keyed by owner in memory and Postgres | Two-int4 advisory form mixed up with the old bigint key |

**Prerequisites:** S-04 archived (done). `TEST_DATABASE_URL` for the Postgres lane.
**Estimated effort:** About the size of S-04; one context, four phases.

## Open Risks & Assumptions

- The `distill_cards.owner_id` predicate is unindexed. This is accepted at a two-person scale.
- `hashtext` collisions serialize two people and never leak data.
- A database holding sittings must be emptied before upgrading, as in S-04.

## Success Criteria (Summary)

- Person B sees nothing due and cannot open, read, grade, or reject over person A's cards or sitting.
- Two people's remember units of work run concurrently, and one person's stay serialized.
- The offline suite, the Postgres lane, and basedpyright are green.
