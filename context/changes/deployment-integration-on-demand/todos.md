---
change_id: deployment-integration-on-demand
current_phase: 1
next_step: 1.3
next_command: /implement deployment-integration-on-demand phase 1
updated: 2026-09-14
---

### Phase 1: On-Demand Integration Workflow

#### Automated

- [x] 1.1 Actionlint reports no errors on integration.yml
- [x] 1.2 workflow_dispatch is the only trigger key

#### Manual

- [ ] 1.3 Dispatch against the branch head runs both suites green with a healthy Postgres service
- [ ] 1.4 Dispatch against an older main SHA checks out and tests that commit
- [ ] 1.5 No run appears from a push or from opening the pull request

### Phase 2: Commit Status on the Tested SHA

#### Automated

- [ ] 2.1 Actionlint reports no errors on integration.yml
- [ ] 2.2 The final status step is guarded by if always

#### Manual

- [ ] 2.3 Tested SHA shows integration pending while the run is in flight
- [ ] 2.4 Tested SHA shows integration success linking to the run
- [ ] 2.5 A red run leaves integration failure on its SHA rather than a stuck pending
- [ ] 2.6 The branch head the workflow was launched from carries no integration status
- [ ] 2.7 Open pull requests stay mergeable with integration absent from the ruleset

### Phase 3: Record the Lane for People and Agents

#### Automated

- [ ] 3.1 Both agent guides carry the integration line and remain identical
