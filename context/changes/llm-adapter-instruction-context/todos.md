---
change_id: llm-adapter-instruction-context
current_phase: 3
next_step: tests
next_command: /unit-test llm-adapter-instruction-context phase 3
updated: 2026-09-12
---

### Phase 1: Pin the shared instruction model

#### Tests

- [x] tests generated — a099d43

#### Automated

- [x] 1.1 Make the instruction-model suite pass, moving code where it disagrees with a docstring — a73c310

### Phase 2: Coverage arithmetic and coverage policy

#### Tests

- [x] tests generated — ad664ea

#### Automated

- [x] 2.1 Implement trend_of over the window and the flat band — 2bac54f
- [x] 2.2 Implement reading_of against COVERAGE_HIGH and the trend — 2bac54f

### Phase 3: Capture's phase builders build

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 Implement CaptureInstructionBuilder.build as the final composition
- [ ] 3.2 Implement ConversingInstructionBuilder.phase_blocks with its two optional blocks
- [ ] 3.3 Implement DraftingInstructionBuilder.phase_blocks with the three draft states and the handoff

### Phase 4: Declare the wiring symbols

#### Automated

- [ ] 4.1 Declare State.instruction_builder and StateMachine.build_instruction
- [ ] 4.2 Rename the tool result to CoverageAssessment with a Coverage field and declare the recording action
- [ ] 4.3 Declare the CoverageAssessed event and add it to the AgentEvent union
- [ ] 4.4 Widen CaptureAgentPort.converse and both adapters with the instruction parameter

### Phase 5: The session keeps what the model assessed

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Implement the recording action and route it from Conversing.get_actions
- [ ] 5.2 Guard the model's float in the assess_coverage handler
- [ ] 5.3 Map CoverageAssessment to CoverageAssessed in the provider adapter
- [ ] 5.4 Yield CoverageAssessed from the deterministic double
- [ ] 5.5 Remove CaptureTurn.coverage_confidence and read the figure from the session
- [ ] 5.6 Move the coverage wrap-up BDD step onto the event

#### Manual

- [ ] 5.7 Run the full backend suite after the rename

### Phase 6: The machine hands the instruction across the port

#### Tests

- [ ] tests generated

#### Automated

- [ ] 6.1 Declare both capture phases' instruction builders
- [ ] 6.2 Implement StateMachine.build_instruction
- [ ] 6.3 Give the 11 fake states an instruction builder
- [ ] 6.4 Pass the instruction from send_message across the port
- [ ] 6.5 Render blocks as the instructions sequence and delete the adapter's prose constants
- [ ] 6.6 Carry the third argument through the agent contract suite

#### Manual

- [ ] 6.7 Run a capture session end to end and confirm reply streaming and the drafting handoff

### Phase 7: The deterministic double speaks from blocks

#### Tests

- [ ] tests generated

#### Automated

- [ ] 7.1 Delete the double's prose constants and speak the handoff block
- [ ] 7.2 Compose the conversational reply from the blocks it was handed
- [ ] 7.3 Branch on the DRAFT_STATE block instead of the note tool names

#### Manual

- [ ] 7.4 Read an in-memory session's reply and trace every sentence to a block
