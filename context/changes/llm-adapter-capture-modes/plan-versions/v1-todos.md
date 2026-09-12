---
change_id: llm-adapter-capture-modes
current_phase: 2
next_step: 2.1
next_command: /unit-test llm-adapter-capture-modes phase 2
updated: 2026-09-12
---

### Phase 1: Graph mechanics bodies and the tool-name invariant

#### Tests

- [x] tests generated — 5fcd343

#### Automated

- [x] 1.1 Graph mechanics suite passes against a non-capture graph — a8793ee
- [x] 1.2 Ruff reports no B027 suppression left in the graph package — a8793ee
- [x] 1.3 Basedpyright reports zero errors over the graph package — a8793ee

### Phase 2: State machine bodies and the transition predicate

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 State machine suite passes, including can_advance and advance
- [ ] 2.2 Basedpyright reports zero errors over the graph package

### Phase 3: Consent and return-to-conversation symbols (stubs)

#### Automated

- [ ] 3.1 Capture graph and turn modules import cleanly
- [ ] 3.2 Basedpyright reports zero errors over the capture domain

### Phase 4: Capture graph behaviour — guards, actions and tool filtering

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Capture graph suite passes, pinning empty terminal states and both edges reachable
- [ ] 4.2 Capture domain model suite passes
- [ ] 4.3 Basedpyright reports zero errors over the domain layer

### Phase 5: Pydantic AI capture agent adapter (stubs)

#### Automated

- [ ] 5.1 Pydantic AI capture agent module imports cleanly
- [ ] 5.2 Embedding adapter suite still passes after the tracing signature change

### Phase 6: Pydantic AI adapter — stream mapping and tracing

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Pydantic AI capture agent suite passes on TestModel and FunctionModel
- [ ] 6.2 Capture agent contract suite passes for the Pydantic AI implementation
- [ ] 6.3 Basedpyright reports zero errors over the adapters layer

#### Manual

- [ ] 6.4 Confirm one real capture turn groups its observations under the session id in Langfuse

### Phase 7: Deterministic in-memory capture agent adapter (stubs)

#### Automated

- [ ] 7.1 Deterministic capture agent module imports cleanly

### Phase 8: Deterministic adapter behaviour and message history

#### Tests

- [ ] tests generated

#### Automated

- [ ] 8.1 Message repository contract suite passes with nothing skipped
- [ ] 8.2 Capture agent contract suite passes for both implementations
- [ ] 8.3 Basedpyright reports zero errors over src and tests

### Phase 9: Command rewrite — one port and the turn loop

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Send-message command suite passes, covering both segments and rollback
- [ ] 9.2 Basedpyright reports zero errors over the application layer

#### Manual

- [ ] 9.3 Stream two turns over HTTP and confirm draft events arrive in the consent turn

### Phase 10: Remove the superseded ports and rewire composition

#### Automated

- [ ] 10.1 Full pytest run passes, including the distill-flow features
- [ ] 10.2 Ruff is clean over src and tests
- [ ] 10.3 Basedpyright reports zero errors over src and tests
- [ ] 10.4 Grep finds no superseded port or ReplyChunk reference

#### Manual

- [ ] 10.5 Walk one session end to end over HTTP and confirm the SSE sequence is unchanged
