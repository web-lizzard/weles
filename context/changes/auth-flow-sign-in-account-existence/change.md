---
change_id: auth-flow-sign-in-account-existence
title: A valid sign-in token also confirms the account still exists
status: implementing
created: 2026-09-14
updated: 2026-09-14
archived_at: null
origin: auth-flow-sign-in-lifetime
---

## Notes

Dodać guard: SignInVerifier.verify() dla poprawnie podpisanego, nie wygasłego tokenu ma dodatkowo sprawdzić w AccountStore, że użytkownik nadal istnieje (konto mogło zostać usunięte). Zły/niepoprawny token nadal ma być odrzucany bez dotykania bazy (FR-009 zachowane dla nieprawidłowych callerów), ale dobry token nie może już ufać wyłącznie podpisowi JWT — musi zweryfikować istnienie konta.
