---
description: Chat in the user's language; artifacts in English unless told otherwise
alwaysApply: true
---

# Language Policy

## Chat responses

Match the language the user writes in.

- User writes in Polish → reply in Polish.
- User writes in English → reply in English.
- Mixed input → follow the dominant language of the latest message.

This applies to explanations, questions, and summaries in the chat window only.

## Artifacts (default: English)

Write all durable project output in **English**, unless the user explicitly requests another language for that item.

Artifacts include:

- Files created or edited on disk (docs, README, `context/`, configs, comments)
- Commit messages and PR titles/descriptions
- Code identifiers, error messages, and user-facing strings (unless i18n is in scope)
- Rule, skill, and agent instruction content

### Override

Only switch artifact language when the user clearly asks, e.g.:

- "write the README in Polish"
- "commit message in Polish"
- "comments in PL for this file"

Without an explicit override, keep artifacts in English even when the chat is in another language.
