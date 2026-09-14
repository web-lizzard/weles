---
change_id: auth-flow-sign-in-account-existence
current_phase: 1
next_step: 1.1
next_command: /unit-test auth-flow-sign-in-account-existence phase 1
updated: 2026-09-14
---

### Phase 1: Account-existence guard — stubs

#### Automated

- [ ] 1.1 Add `AccountStore.exists` to the port
- [ ] 1.2 Add `exists` stubs to `InMemoryAccountStore` and `SqlAlchemyAccountStore`
- [ ] 1.3 Add `AccountNoLongerExistsError`
- [ ] 1.4 `SignInTokens.__init__` takes `accounts: AccountStore`
- [ ] 1.5 Narrow `SignInVerifier`'s no-I/O docstring invariant

### Phase 2: Account-existence guard — behavior

#### Tests

- [ ] tests generated

#### Automated

- [ ] 2.1 Implement `InMemoryAccountStore.exists`
- [ ] 2.2 Implement `SqlAlchemyAccountStore.exists`
- [ ] 2.3 Implement the `verify()` existence guard
- [ ] 2.4 Wire shared `AccountStore` in `compose.py`
- [ ] 2.5 Map `account_no_longer_exists` to 401
- [ ] 2.6 Fix `test_authenticator.py`'s `SignInTokens(...)` call site
