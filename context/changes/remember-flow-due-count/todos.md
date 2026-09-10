---
change_id: remember-flow-due-count
current_phase: 6
next_step: 6.4
next_command: /implement remember-flow-due-count phase 6
updated: 2026-09-10
---

### Phase 1: Due partition stubs

#### Automated

- [x] 1.1 Add DuePartition and the partition_due signature in domain/remember/due_partition.py — 5038d5a

### Phase 2: Due partition behaviour

#### Tests

- [x] tests generated — 0be2699

#### Automated

- [x] 2.1 Compute the total and the three buckets over due union outstanding — 73ec3a3
- [x] 2.2 Branch the no-sitting case to put the whole total in not_yet_seen — 73ec3a3

### Phase 3: DTO, query, route and composition stubs

#### Automated

- [x] 3.1 Add DuePartitionDTO and DueCountDTO, and the defaulted due field on PresentedCardDTO and GradeAppliedDTO — 4b38f60
- [x] 3.2 Add DueCountQuery with ports injected directly — 4b38f60
- [x] 3.3 Add GET /due-cards/count and the get_due_count_query factory in compose — 4b38f60
- [x] 3.4 Add the due_count seam to InMemoryRememberComposition — 4b38f60

#### Manual

- [x] 3.5 Curl /due-cards/count against a running backend and confirm a zero partition with HTTP 200 — 4b38f60

### Phase 4: Acceptance layer for AC-14 and AC-15

#### Manual

- [x] 4.1 Author the AC-14 and AC-15 scenarios via /bdd — 429038f
- [x] 4.2 Confirm the new scenarios fail on assertions, not collection — 429038f
- [x] 4.3 Confirm no existing remember-flow scenario regressed — 429038f

### Phase 5: Due count query and route behaviour

#### Tests

- [x] tests generated — 5183b57

#### Automated

- [x] 5.1 Assemble the four readings and return a real partition from DueCountQuery — 25455f6
- [x] 5.2 Treat a sitting past its resume horizon as absent — 25455f6

#### Manual

- [x] 5.3 Curl /due-cards/count against a seeded backend and confirm the buckets sum to the total — 25455f6

### Phase 6: Partition on sitting responses

#### Tests

- [x] tests generated — d30ee6b

#### Automated

- [x] 6.1 Populate due on the open and resume responses in OpenSittingCommand
- [x] 6.2 Populate due on the grade response in GradeCardCommand
- [x] 6.3 Populate due on the current-card response in CurrentCardQuery

#### Manual

- [ ] 6.4 Confirm seen_still_owed is zero on a fresh sitting and non-zero after a hard grade

### Phase 7: TUI API client and due store stubs

#### Automated

- [ ] 7.1 Add api/due.ts with DuePartition and the fetchDueCount signature
- [ ] 7.2 Add store/due.ts and hooks/useDuePolling.ts on the notesStore polling shape

#### Manual

- [ ] 7.3 Regenerate schema.d.ts against a running backend

### Phase 8: Due client and store behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Map the nested due object in one shared helper used by due.ts and sittings.ts
- [ ] 8.2 Keep the last partition and set isStale on a failed fetch
- [ ] 8.3 Start and stop the 15-second poll idempotently
- [ ] 8.4 Push the due object from open and grade responses into dueStore

### Phase 9: Shell row and overlay geometry

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Add DueCountHeader rendering the total, dimmed when stale
- [ ] 9.2 Mount the header and the poll in app.tsx and shift both overlays to top 1
- [ ] 9.3 Update app, noteListOverlay and sittingOverlay tests to the shifted geometry

#### Manual

- [ ] 9.4 Confirm the count row survives both overlays against a live backend

### Phase 10: Breakdown in the sitting overlay

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Replace the outstanding count footer with the total and its non-zero buckets

#### Manual

- [ ] 10.2 Grade a card hard in a live review and confirm header and overlay totals move together
