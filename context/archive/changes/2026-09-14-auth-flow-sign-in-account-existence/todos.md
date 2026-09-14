---
change_id: auth-flow-sign-in-account-existence
current_phase: 2
next_step: done
next_command: /impl-review auth-flow-sign-in-account-existence
updated: 2026-09-14
---

### Phase 1: Account-existence guard — stubs

#### Automated

- [x] 1.1 Add `AccountStore.exists` to the port — 360b20c
- [x] 1.2 Add `exists` stubs to `InMemoryAccountStore` and `SqlAlchemyAccountStore` — 360b20c
- [x] 1.3 Add `AccountNoLongerExistsError` — 360b20c
- [x] 1.4 `SignInTokens.__init__` takes `accounts: AccountStore` — 360b20c
- [x] 1.5 Narrow `SignInVerifier`'s no-I/O docstring invariant — 360b20c

Note: Phase 1's stub commit was folded into Phase 2's implementation commit —
see Phase 2 below. `basedpyright` and the full suite are green as of that
commit.

### Phase 2: Account-existence guard — behavior

#### Tests

- [x] tests generated — f42b8b8

#### Automated

- [x] 2.1 Implement `InMemoryAccountStore.exists` — 360b20c
- [x] 2.2 Implement `SqlAlchemyAccountStore.exists` — 360b20c
- [x] 2.3 Implement the `verify()` existence guard — 360b20c
- [x] 2.4 Wire shared `AccountStore` in `compose.py` — 360b20c
- [x] 2.5 Map `account_no_longer_exists` to 401 — 360b20c
- [x] 2.6 Fix `test_authenticator.py`'s `SignInTokens(...)` call site — f42b8b8
