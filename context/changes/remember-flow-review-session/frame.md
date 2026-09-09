---
status: closed
created: 2026-09-09
updated: 2026-09-09
---

## Boundaries

In scope:

**What the change delivers**

- The first review sitting end to end: opening a session over what is due, presenting one card at a time, revealing a back on request, taking a four-step grade, and moving that card's schedule on.
- Five seams, all behind in-memory adapters as every existing repository already is: a scheduling port with its `fsrs` adapter; a port onto distill resolving candidate cards and the content a review renders; a repository for the sitting; a store for review events that saves one event and answers queries by card and by sitting; and a repository for each card's memoized scheduling state.
- The domain depends on no scheduling library. Everything that knows the library's vocabulary lives behind the scheduling port, and no part of the domain loads the review log as a whole.

**The sitting**

- A sitting has an identity that outlives a single request, and its frozen membership is retrievable by that identity for as long as it runs — a sitting spans many requests and exists from the moment it opens, before any card is graded.
- It records only what the review log cannot: its identity, the set of cards chosen when it opened, and when it opened. How often a card has been shown, which cards are finished, how far along it is and which card comes next are derived from the log and stored nowhere. The record is written once and never changed.
- It is recorded apart from the review log, which carries only events that change a card's schedule.
- Leaving a sitting unfinished is a supported and lossless outcome, not an error: every grade already given is permanent and has already moved its card, and whatever was not reached is still due next time. It follows that reaching completion is not the first-run path, since a large first due set will not be exhausted.

**What happens inside one**

- Nothing bounds the size of a sitting. A card belongs to it when it has no scheduling record or its next-due date has passed, so a sitting may contain the whole backlog, and no cap on cards or on never-reviewed intake exists in this change.
- A card discarded elsewhere while a sitting is running drops out of it when the set is read, rather than being removed from it.
- Completion is derived from the grades recorded for that sitting, never from a card's next-due date. A card is finished once it has been graded `Good` or better in that sitting, or shown a configured number of times in it. Completion is therefore monotone and needs no stored cursor and no stored ordering.
- A card graded below `Good` returns within the same sitting; `Hard` returns it as surely as the lowest grade does.
- The card presented next is drawn at random from the undone cards shown fewest times in this sitting, under the invariant that no card is presented while another undone card in the frozen set has a strictly lower showing count. A sitting is therefore at most as many rounds as that configured count, and a card just graded is never the next card shown.
- The configured showing count is an environment setting, alongside the domain tunables already in `backend/src/config/settings.py`.
- The completion rule and the ordering rule each exist once, as a named concept in the domain rather than as a condition inlined at the point of use, and neither is substitutable: there is one of each and no stored choice between alternatives. The ordering's random source is injectable so it can be made deterministic under test, which is a different thing from making the rule itself substitutable.

**What is recorded, and what can be rebuilt from it**

- A review event records the card, the moment, the grade, and which sitting it belongs to. The sitting holds no reference to its events, and neither knows the other's type.
- The sitting's identity is never read when a card's schedule is reconstructed, so the same events serve the schedule and the sitting without either reader needing the other's fields.
- The timestamp recorded for a review is the same value handed to the scheduler: captured once, timezone-aware UTC, never re-derived or rounded on either path.
- A card's scheduling state is held per card as a next-due date the domain owns and indexes, an opaque value the domain never interprets, and a stamp naming the algorithm and parameter version that produced it. It is created on a card's first review, so its absence is what makes a card never-reviewed and therefore due.
- That record is a cache of the review log and never a second source of truth. It can be discarded at any moment and rebuilt on the read path, which is what lets a stale stamp be detected lazily with no background process.
- A card's scheduling state is fully reconstructible from the review log alone: replaying that card's events in order reproduces the same next-due date, interval fuzz included. The fuzz draw is derived from each event's own recorded facts, so no seed and no interval is stored anywhere.
- Grading a card records the event and updates that card's memoized scheduling state together. Of the two, the event is the one that must not be lost: the memoized state can always be rebuilt from it, and the reverse does not hold.
- The sitting itself is not reconstructible, and is not required to be — which card was shown when, and how many rounds ran, changes no card's schedule.

Out of scope:

- Every acceptance criterion belonging to a later slice on the `remember-flow` roadmap: AC-10 through AC-22 (resume, expiry, due count, capture prompt, rejection, source jump, capture entry).
- Expiry of a sitting, and offering an unfinished one back to the user. Those arrive with S-02 and no work here anticipates them.
- Topic- or note-scoped selection, and batch-of-N or timebox session modes, both effort-level non-goals in `prd.md`. This change carries one selection and one completion rule, and the port resolving candidate cards takes no scope argument while "everything" is its only value.
- Any substitutable policy for selection or completion, and any field on the sitting recording which policy it began under.

## Requirements

The single authority for these is `context/efforts/remember-flow/stories.md`; they are cited here and not restated.

- AC-01, AC-02 — from US-01.
- AC-03, AC-04, AC-05 — from US-02.
- AC-06, AC-07, AC-08 — from US-03.
- AC-09 — from US-04.
