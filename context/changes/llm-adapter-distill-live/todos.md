---
change_id: llm-adapter-distill-live
current_phase: 7
next_step: 7.0
next_command: /unit-test llm-adapter-distill-live phase 7
updated: 2026-09-13
---

### Phase 1: Guard-selected move on the shared machine

#### Tests

- [x] tests generated — 7b72d51

#### Automated

- [x] 1.1 Graph machine suite passes — ab1e081
- [x] 1.2 basedpyright clean over src/domain/shared — ab1e081

### Phase 2: Review grade and regeneration policy rules

#### Tests

- [x] tests generated — 8967851

#### Automated

- [x] 2.1 Value object and regeneration policy suites pass — cbb6b4e

### Phase 3: Minting a round on the run

#### Tests

- [x] tests generated — bc7352f

#### Automated

- [x] 3.1 Run minting suite passes — 3cf8cb2

### Phase 4: Review verdicts, share, and gaps on the run

#### Tests

- [x] tests generated — 979f2e5

#### Automated

- [x] 4.1 Run review suite passes — 5279f1f

### Phase 5: Merge on the run

#### Tests

- [x] tests generated — f8638c8

#### Automated

- [x] 5.1 Run merge suite passes — 26c0b1e

### Phase 6: Distill instruction builders

#### Tests

- [x] tests generated — 26ce180

#### Automated

- [x] 6.1 Distill instructions suite passes — <PENDING_SHA>

### Phase 7: Distill machine wiring and route

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Distill flow suite passes
- [ ] 7.2 basedpyright clean over src/domain

### Phase 8: Deterministic structured task adapter

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Structured task port contract and deterministic adapter suites pass

### Phase 9: Command walks the flow; old seam removed

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Distill unit suite passes
- [ ] 9.2 BDD distill-flow scenarios pass
- [ ] 9.3 Integration suite passes
- [ ] 9.4 adapters.compose imports
- [ ] 9.5 No CardGeneration reference remains under backend

### Phase 10: pydantic-ai structured task adapter

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 pydantic-ai structured task suite passes
- [ ] 10.2 basedpyright clean over src/adapters

### Phase 11: Live composition and run tracing

#### Tests

- [ ] tests generated

#### Automated

- [ ] 11.1 Full backend suite passes
- [ ] 11.2 basedpyright clean
- [ ] 11.3 ruff check clean over src and tests

#### Manual

- [ ] 11.4 Live run against OpenRouter persists grounded cards and note ends ready
- [ ] 11.5 Langfuse shows one distill_run session per note with per-phase child spans
- [ ] 11.6 One-sentence note ends ready with zero live cards
