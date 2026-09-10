---
effort_id: remember-flow
created: 2026-09-09
updated: 2026-09-10
---

## At a glance

| ID | Outcome | Change ID | Status |
|----|---------|-----------|--------|
| S-01 | Users can work through every due card in one review sitting — graded cards reschedule themselves | remember-flow-review-session | done |
| S-02 | Users can leave a review mid-way and pick up where they left off | remember-flow-session-resume | in_progress |
| S-03 | Users can see how many cards are due without opening a review | remember-flow-due-count | pending |
| S-04 | Users can reject a bad card during review so it stops coming back | remember-flow-card-rejection | pending |
| S-05 | Users can jump from a card under review to its source passage | remember-flow-source-jump | pending |
| S-06 | Users can open a review from inside capture and return without losing the conversation | remember-flow-capture-entry | pending |
| S-07 | Users learn about waiting cards when a capture session closes | remember-flow-capture-prompt | pending |

## Dependencies

```mermaid
flowchart LR
  S-01["S-01 · review session core"] --> S-02["S-02 · leave & resume"]
  S-01 --> S-03["S-03 · due count"]
  S-01 --> S-04["S-04 · card rejection"]
  S-01 --> S-05["S-05 · source jump"]
  S-01 --> S-06["S-06 · capture entry"]
  S-03 --> S-07["S-07 · capture prompt"]
```

## Slices

### S-01: Users can work through every due card in one review sitting — graded cards reschedule themselves

- **Outcome:** Users can work through every due card in one review sitting — graded cards reschedule themselves
- **Acceptance criteria:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09
- **Change ID:** remember-flow-review-session
- **Status:** done

### S-02: Users can leave a review mid-way and pick up where they left off

- **Outcome:** Users can leave a review mid-way and pick up where they left off
- **Acceptance criteria:** AC-10, AC-11, AC-12, AC-13
- **Change ID:** remember-flow-session-resume
- **Status:** in_progress
- **Prerequisites:** S-01
- **Parallel with:** S-03, S-04, S-05, S-06

### S-03: Users can see how many cards are due without opening a review

- **Outcome:** Users can see how many cards are due without opening a review
- **Acceptance criteria:** AC-14, AC-15
- **Change ID:** remember-flow-due-count
- **Status:** pending
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-04, S-05, S-06

### S-04: Users can reject a bad card during review so it stops coming back

- **Outcome:** Users can reject a bad card during review so it stops coming back
- **Acceptance criteria:** AC-17
- **Change ID:** remember-flow-card-rejection
- **Status:** pending
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-03, S-05, S-06

### S-05: Users can jump from a card under review to its source passage

- **Outcome:** Users can jump from a card under review to its source passage
- **Acceptance criteria:** AC-18, AC-19, AC-20
- **Change ID:** remember-flow-source-jump
- **Status:** pending
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-03, S-04, S-06

### S-06: Users can open a review from inside capture and return without losing the conversation

- **Outcome:** Users can open a review from inside capture and return without losing the conversation
- **Acceptance criteria:** AC-21, AC-22
- **Change ID:** remember-flow-capture-entry
- **Status:** pending
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-03, S-04, S-05

### S-07: Users learn about waiting cards when a capture session closes

- **Outcome:** Users learn about waiting cards when a capture session closes
- **Acceptance criteria:** AC-16
- **Change ID:** remember-flow-capture-prompt
- **Status:** pending
- **Prerequisites:** S-03

## Done

- **S-01: Users can work through every due card in one review sitting — graded cards reschedule themselves** — Archived 2026-09-10 → `context/archive/changes/2026-09-09-remember-flow-review-session/`. Lesson: —.
