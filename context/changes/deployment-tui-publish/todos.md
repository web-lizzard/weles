---
change_id: deployment-tui-publish
current_phase: 1
next_step: 1.1
next_command: /implement deployment-tui-publish phase 1
updated: 2026-09-14
---

### Phase 1: Installable TUI Package

#### Automated

- [ ] 1.1 TUI typecheck, tests and lint pass
- [ ] 1.2 Build and pack produce a tarball containing dist/cli.js

#### Manual

- [ ] 1.3 Tarball installs into a temp prefix and weles prints version and help

### Phase 2: Release Workflow and Install Docs

#### Automated

- [ ] 2.1 Actionlint reports no errors on tui-release.yml

#### Manual

- [ ] 2.2 Pushing tui-v0.1.0 creates a release with both tarballs
- [ ] 2.3 Anonymous install from the release URL in a clean node:22 container prints 0.1.0
