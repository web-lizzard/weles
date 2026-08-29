---
change_id: backend-agentic-rules
current_phase: 3
next_step: 3.1
next_command: /unit-test backend-agentic-rules phase 3
updated: 2026-08-29
---

### Phase 1: Agentic rules content and wiring

#### Automated

- [x] 1.1 Write context/foundation/rules/layering.md — 4a964f1
- [x] 1.2 Write context/foundation/rules/cqrs-lite.md — 4a964f1
- [x] 1.3 Write context/foundation/rules/contract-testing.md — 4a964f1
- [x] 1.4 Write context/foundation/rules/exceptions.md — 4a964f1
- [x] 1.5 Symlink .claude/rules/*.md (4 topics) to canonical files — 4a964f1
- [x] 1.6 Symlink .cursor/rules/*.mdc (4 topics) to canonical files — 4a964f1

#### Manual

- [x] 1.7 Verify Claude Code loads a rule via /context when reading a backend/ file — 4a964f1
- [x] 1.8 Verify Cursor activates the rule when editing a backend/ file — 4a964f1

### Phase 2: CoreException stubs

#### Automated

- [x] 2.1 Add CoreException class stub + code() signature in backend/src/domain/exceptions.py — 1e7334b

### Phase 3: CoreException behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 3.1 Implement __init_subclass__ auto-derivation of code (snake_case, strip Error/Exception)
- [ ] 3.2 Implement explicit _code override support

### Phase 4: HTTP exception-mapping stubs

#### Automated

- [ ] 4.1 Add empty EXCEPTION_STATUS_MAP + core_exception_handler stub in backend/src/adapters/http/errors.py
- [ ] 4.2 Register handler in backend/src/main.py

### Phase 5: HTTP exception-mapping behavior and exhaustiveness test

#### Tests

- [ ] tests generated

#### Automated

- [ ] 5.1 Add NotFoundError(CoreException) mapped to HTTP 404 in EXCEPTION_STATUS_MAP
- [ ] 5.2 Implement core_exception_handler response shape ({"code": ..., "detail": ...})
- [ ] 5.3 Implement exhaustiveness test walking CoreException.__subclasses__() recursively
