---
change_id: auth-flow-sign-in-account-existence
current_phase: 2
next_step: 2.1
next_command: /implement auth-flow-sign-in-account-existence phase 2
updated: 2026-09-14
---

### Phase 1: Account-existence guard — stubs

#### Automated

- [x] 1.1 Add `AccountStore.exists` to the port
- [x] 1.2 Add `exists` stubs to `InMemoryAccountStore` and `SqlAlchemyAccountStore`
- [x] 1.3 Add `AccountNoLongerExistsError`
- [x] 1.4 `SignInTokens.__init__` takes `accounts: AccountStore`
- [x] 1.5 Narrow `SignInVerifier`'s no-I/O docstring invariant

Note: Phase 1's stub commit was folded into Phase 2's implementation commit —
see Phase 2 below. `basedpyright` and the full suite are green as of that
commit.

### Phase 2: Account-existence guard — behavior

#### Tests

- [x] tests generated — f42b8b8

#### Automated

- [x] 2.1 Implement `InMemoryAccountStore.exists`
- [x] 2.2 Implement `SqlAlchemyAccountStore.exists`
- [x] 2.3 Implement the `verify()` existence guard
- [x] 2.4 Wire shared `AccountStore` in `compose.py`
- [x] 2.5 Map `account_no_longer_exists` to 401
- [x] 2.6 Fix `test_authenticator.py`'s `SignInTokens(...)` call site — f42b8b8
