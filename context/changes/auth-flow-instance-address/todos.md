---
change_id: auth-flow-instance-address
current_phase: 2
next_step: 2.1
next_command: /unit-test auth-flow-instance-address phase 2
updated: 2026-09-13
---

### Phase 1: Instance address stubs

#### Automated

- [x] 1.1 Add InstanceAddress, InvalidInstanceAddressError and the parseInstanceAddress signature in instance/address.ts — a2d37e9
- [x] 1.2 Add ConfigLocation and the config store signatures in instance/configStore.ts — a2d37e9
- [x] 1.3 Add InstanceCommandDeps and the runInstanceCommand signature in instance/command.ts — a2d37e9
- [x] 1.4 Pass pnpm typecheck and pnpm lint — a2d37e9

### Phase 2: Instance address behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Validate scheme, credentials, query and fragment and trim the trailing slash in parseInstanceAddress
- [ ] 2.2 Read and write instanceAddress in the XDG config file with a home-directory fallback
- [ ] 2.3 Show the stored address and set a replacement through runInstanceCommand with exit codes 0, 1 and 2
- [ ] 2.4 Pass pnpm test, pnpm typecheck and pnpm lint

### Phase 3: Startup and API routing stubs

#### Automated

- [ ] 3.1 Add InstanceNotConfiguredError, setInstanceAddress, instanceAddress and getClient signatures in api/instance.ts
- [ ] 3.2 Add StartupDecision and the resolveStartup signature in startup.ts
- [ ] 3.3 Add test/setup.ts configuring http://localhost:8000 and register it in vitest setupFiles
- [ ] 3.4 Pass pnpm typecheck and pnpm lint

### Phase 4: Startup and API routing behaviour

#### Tests

- [ ] tests generated

#### Automated

- [ ] 4.1 Hold the process address and memoize the openapi client per address in api/instance.ts
- [ ] 4.2 Move every API module to getClient and remove both hardcoded addresses
- [ ] 4.3 Return ready or missing from resolveStartup
- [ ] 4.4 Dispatch the instance command before the TTY check and refuse to start without an instance in cli.tsx
- [ ] 4.5 Pass pnpm test, pnpm typecheck and pnpm lint

#### Manual

- [ ] 4.6 Run the built TUI with an empty config directory and confirm the refusal message and exit code 1
- [ ] 4.7 Set an ftp address and confirm the scheme error and exit code 2
- [ ] 4.8 Set http://localhost:8000/ and confirm weles instance prints it without the trailing slash
- [ ] 4.9 Start the TUI against a running backend and confirm notes and due count load
- [ ] 4.10 Set a port with no backend and confirm the TUI shows load failures and none of the previous notes
- [ ] 4.11 Confirm dist/cli.js contains no localhost:8000
