---
change_id: deployment-integration-on-demand
current_phase: 3
next_step: ""
next_command: /archive deployment-integration-on-demand
updated: 2026-09-14
---

### Phase 1: On-Demand Integration Workflow

#### Automated

- [x] 1.1 Actionlint reports no errors on integration.yml — d41e428
- [x] 1.2 workflow_dispatch is the only trigger key — d41e428

#### Manual

- [x] 1.3 Dispatch against the branch head runs both suites green with a healthy Postgres service
- [x] 1.4 Dispatch against an older main SHA checks out and tests that commit
- [x] 1.5 No run appears from a push or from opening the pull request

### Phase 2: Commit Status on the Tested SHA

#### Automated

- [x] 2.1 Actionlint reports no errors on integration.yml — e2eb4f3
- [x] 2.2 The final status step is guarded by if always — e2eb4f3

#### Manual

- [x] 2.3 Tested SHA shows integration pending while the run is in flight
- [x] 2.4 Tested SHA shows integration success linking to the run
- [x] 2.5 A red run leaves integration failure on its SHA rather than a stuck pending
- [x] 2.6 The branch head the workflow was launched from carries no integration status
- [x] 2.7 Open pull requests stay mergeable with integration absent from the ruleset

### Phase 3: Record the Lane for People and Agents

#### Automated

- [x] 3.1 Both agent guides carry the integration line and remain identical — a309fef
