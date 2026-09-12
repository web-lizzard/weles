---
change_id: llm-adapter-capture-modes
current_phase: 12
next_step: 12.4
next_command: /implement llm-adapter-capture-modes phase 12
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

- [x] tests generated — 89c4873

#### Automated

- [x] 5.1 Capture graph suite passes, pinning empty terminal states, both edges reachable, and at most one transition available — e0cfce9
- [x] 5.2 Capture domain model suite passes — e0cfce9
- [x] 5.3 Basedpyright reports zero errors over the domain layer — e0cfce9

#### Triage

- [x] 5.4 R5-F2 Capture graph tests must assert CaptureSession.start() stamps UTC-aware created_at — 48fd3f4

### Phase 6: Message-recording events and the agent/command event split (stubs)

#### Automated

- [x] 6.1 AgentEvent and the two message events import by name — c3d778c
- [x] 6.2 Basedpyright reports zero errors over the capture domain — c3d778c

### Phase 7: A turn's own messages reach the machine

#### Tests

- [x] tests generated — e8cd947

#### Automated

- [x] 7.1 Capture graph suite passes, including consent recorded from the turn's own first message — 72b0247
- [x] 7.2 Basedpyright reports zero errors over the domain layer — 72b0247

### Phase 8: Pydantic AI capture agent adapter (stubs)

#### Automated

- [x] 8.1 Pydantic AI capture agent module imports cleanly — f64b708
- [x] 8.2 Embedding adapter suite still passes after the tracing signature change — f64b708

### Phase 9: Pydantic AI adapter — stream mapping and tracing

#### Tests

- [x] tests generated — 1c11ef4

#### Automated

- [x] 9.1 Pydantic AI capture agent suite passes on TestModel and FunctionModel — 91093b5
- [x] 9.2 Capture agent contract suite passes for the Pydantic AI implementation — 91093b5
- [x] 9.3 Basedpyright reports zero errors over the adapters layer — 91093b5

#### Manual

- [ ] 9.4 Confirm one real capture turn groups its observations under the session id in Langfuse

### Phase 10: Deterministic in-memory capture agent adapter (stubs)

#### Automated

- [x] 10.1 Deterministic capture agent module imports cleanly — 034d08d

### Phase 11: Deterministic adapter behaviour and message history

#### Tests

- [x] tests generated — 034d08d

#### Automated

- [x] 11.1 Message repository contract suite passes with nothing skipped — 034d08d
- [x] 11.2 Capture agent contract suite passes for both implementations — 034d08d
- [x] 11.3 Basedpyright reports zero errors over src and tests — 034d08d

### Phase 12: Command rewrite — one port and the turn loop

#### Tests

- [x] tests generated — db334d8

#### Automated

- [x] 12.1 Send-message command suite passes, covering both segments and rollback
- [x] 12.2 No turn opens a third segment
- [x] 12.3 Basedpyright reports zero errors over the application layer

#### Manual

- [ ] 12.4 Stream two turns over HTTP and confirm draft events arrive in the consent turn

### Phase 13: Remove the superseded ports and rewire composition

#### Automated

- [ ] 13.1 Full pytest run passes, including the distill-flow features
- [ ] 13.2 Ruff is clean over src and tests
- [ ] 13.3 Basedpyright reports zero errors over src and tests
- [ ] 13.4 Grep finds no superseded port or ReplyChunk reference

#### Manual

- [ ] 13.5 Walk one session end to end over HTTP and confirm the SSE sequence is unchanged

### Phase 14: Dependencies reach actions

#### Tests

- [ ] tests generated

#### Automated

- [ ] 14.1 Graph mechanics suite passes, asserting deps reach both actions and edge actions
- [ ] 14.2 Capture suites pass unchanged after the widening
- [ ] 14.3 Basedpyright reports zero errors over src and tests

### Phase 15: Vocabulary resolution and the dependency set move into the domain (stubs)

#### Automated

- [ ] 15.1 CaptureDeps, NoteDraft, DraftCompleted and the moved resolver import by name
- [ ] 15.2 Full pytest run passes after the relocation
- [ ] 15.3 Basedpyright reports zero errors over src and tests

### Phase 16: Drafting actions build the note

#### Tests

- [ ] tests generated

#### Automated

- [ ] 16.1 Capture graph suite passes, covering first draft, redraft and a tag before a topic
- [ ] 16.2 Capture domain suites pass
- [ ] 16.3 Basedpyright reports zero errors over src and tests

### Phase 17: The command stops resolving vocabulary

#### Tests

- [ ] tests generated

#### Automated

- [ ] 17.1 Send-message command suite passes for a drafting and a redrafting turn
- [ ] 17.2 Full pytest run passes across every suite
- [ ] 17.3 Ruff is clean over src and tests
- [ ] 17.4 Basedpyright reports zero errors over src and tests
- [ ] 17.5 Grep finds no resolved_topic, resolved_tags or draft_text on _TurnBuffers

#### Manual

- [ ] 17.6 Stream one drafting turn over HTTP and confirm the draft event sequence is unchanged
