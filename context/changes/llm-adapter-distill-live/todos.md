---
change_id: llm-adapter-distill-live
current_phase: 13
next_step: —
next_command: /archive llm-adapter-distill-live
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

- [x] 6.1 Distill instructions suite passes — 4f80184

### Phase 7: Distill machine wiring and route

#### Tests

- [x] tests generated — efc7b00

#### Automated

- [x] 7.1 Distill flow suite passes — 79a27ed
- [x] 7.2 basedpyright clean over src/domain — 79a27ed

### Phase 8: Deterministic structured task adapter — stubs and interfaces

#### Automated

- [x] 8.1 Deterministic structured task adapter module imports — 5ff28a0
- [x] 8.2 basedpyright clean over the deterministic structured task module — 5ff28a0

### Phase 9: Deterministic structured task adapter

#### Tests

- [x] tests generated — 088fd9d

#### Automated

- [x] 9.1 Structured task port contract and deterministic adapter suites pass — 26464b1

### Phase 10: Command walks the flow; old seam removed

#### Tests

- [x] tests generated — 5e5ab8b

#### Automated

- [x] 10.1 Distill unit suite passes — e3d5895
- [x] 10.2 BDD distill-flow scenarios pass — e3d5895
- [x] 10.3 Integration suite passes — e3d5895
- [x] 10.4 adapters.compose imports — e3d5895
- [x] 10.5 No CardGeneration reference remains under backend — e3d5895

### Phase 11: pydantic-ai structured task adapter — stubs and interfaces

#### Automated

- [x] 11.1 pydantic-ai structured task adapter module imports — fead973
- [x] 11.2 basedpyright clean over the pydantic-ai structured task module — fead973

### Phase 12: pydantic-ai structured task adapter

#### Tests

- [x] tests generated — 5173a5c

#### Automated

- [x] 12.1 pydantic-ai structured task suite passes — f2c76ce
- [x] 12.2 basedpyright clean over src/adapters — f2c76ce

### Phase 13: Live composition and run tracing

#### Tests

- [x] tests generated — 12b5889

#### Automated

- [x] 13.1 Full backend suite passes — 0f370b4
- [x] 13.2 basedpyright clean — 0f370b4
- [x] 13.3 ruff check clean over src and tests — 0f370b4

#### Manual

- [x] 13.4 Live run against OpenRouter persists grounded cards and note ends ready
- [x] 13.5 Langfuse shows one distill_run session per note with per-phase child spans
- [x] 13.6 One-sentence note ends ready with zero live cards
