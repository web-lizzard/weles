---
change_id: llm-adapter-capture-modes
current_phase: 5
next_step: 5.1
next_command: /unit-test llm-adapter-capture-modes phase 5
updated: 2026-09-12
---

### Phase 1: Graph mechanics bodies and the tool-name invariant

#### Tests

- [x] tests generated — 5fcd343

#### Automated

- [x] 1.1 Graph mechanics suite passes against a non-capture graph — a8793ee
- [x] 1.2 Ruff reports no B027 suppression left in the graph package — a8793ee
- [x] 1.3 Basedpyright reports zero errors over the graph package — a8793ee

### Phase 2: Edge vocabulary and state descriptions (stubs)

#### Automated

- [x] 2.1 Edge alias symbols import by name — c313c45
- [x] 2.2 Basedpyright reports zero errors over the graph package — c313c45

### Phase 3: State machine behaviour — reporting available transitions

#### Tests

- [x] tests generated — 64ba2f5

#### Automated

- [x] 3.1 State machine suite passes, including available_transitions and refused targets — d3682c9
- [x] 3.2 Graph model suite still passes after the edge alias split — d3682c9
- [x] 3.3 Basedpyright reports zero errors over the graph package — d3682c9

### Phase 4: Consent and return-to-conversation symbols (stubs)

#### Automated

- [x] 4.1 Capture graph and turn modules import cleanly — 33c8d3c
- [x] 4.2 Basedpyright reports zero errors over the capture domain — 33c8d3c

### Phase 5: Capture graph behaviour — guards, actions and tool filtering

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Capture graph suite passes, pinning empty terminal states, both edges reachable, and at most one transition available
- [ ] 5.2 Capture domain model suite passes
- [ ] 5.3 Basedpyright reports zero errors over the domain layer

### Phase 6: Pydantic AI capture agent adapter (stubs)

#### Automated

- [ ] 6.1 Pydantic AI capture agent module imports cleanly
- [ ] 6.2 Embedding adapter suite still passes after the tracing signature change

### Phase 7: Pydantic AI adapter — stream mapping and tracing

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Pydantic AI capture agent suite passes on TestModel and FunctionModel
- [ ] 7.2 Capture agent contract suite passes for the Pydantic AI implementation
- [ ] 7.3 Basedpyright reports zero errors over the adapters layer

#### Manual

- [ ] 7.4 Confirm one real capture turn groups its observations under the session id in Langfuse

### Phase 8: Deterministic in-memory capture agent adapter (stubs)

#### Automated

- [ ] 8.1 Deterministic capture agent module imports cleanly

### Phase 9: Deterministic adapter behaviour and message history

#### Tests

- [ ] tests generated

#### Automated

- [ ] 9.1 Message repository contract suite passes with nothing skipped
- [ ] 9.2 Capture agent contract suite passes for both implementations
- [ ] 9.3 Basedpyright reports zero errors over src and tests

### Phase 10: Command rewrite — one port and the turn loop

#### Tests

- [ ] tests generated

#### Automated

- [ ] 10.1 Send-message command suite passes, covering both segments and rollback
- [ ] 10.2 No turn opens a third segment
- [ ] 10.3 Basedpyright reports zero errors over the application layer

#### Manual

- [ ] 10.4 Stream two turns over HTTP and confirm draft events arrive in the consent turn

### Phase 11: Remove the superseded ports and rewire composition

#### Automated

- [ ] 11.1 Full pytest run passes, including the distill-flow features
- [ ] 11.2 Ruff is clean over src and tests
- [ ] 11.3 Basedpyright reports zero errors over src and tests
- [ ] 11.4 Grep finds no superseded port or ReplyChunk reference

#### Manual

- [ ] 11.5 Walk one session end to end over HTTP and confirm the SSE sequence is unchanged
