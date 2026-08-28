# Duck Sessions

Structured rubber-duck / ideation sessions. One folder per session at `context/duck-sessions/<duck-id>/`, holding two required files and one optional artifact:

```
context/duck-sessions/<duck-id>/
├── duck.md       # identity — frontmatter only
├── log.md        # prose only — current state at top, append-only tagged log below
└── research*.md  # optional — written by /research; not read by any skill yet
```

Both `/new-container duck <duck-id>` and `/duck` write `duck.md` against the identity contract at `references/duck-schema/duck-schema.md` (`duck_id`, `title`, `status`, `created`, `updated`, `archived_at`), and write only prose into `log.md`, against the content contract at `skills/duck/references/log-schema.md`. `status` lives in `duck.md` and only there.

`/research <duck-id>` may add `research.md` or `research-<slug>.md` beside those files. The contract lives at `skills/research/references/research-schema.md` — do not restate it here. No skill reads research from a duck container yet.

Unlike `context/changes/` and `context/efforts/`, a duck session has no fixed end owned by the skill: the user decides when a session is done and graduates it directly into an ADR, a change, or an effort.

Container ids are unique across `context/{changes,efforts,adrs,duck-sessions}/` and `context/archive/` — no two containers of any kind share an id.

Old/completed sessions are archivable, mirroring `/archive` for `context/changes/` (mechanism not yet designed).
