# Architecture Decision Records

Architecture decisions. One folder per ADR at `context/adrs/<adr-id>/`, holding two files:

```
context/adrs/<adr-id>/
├── adr.md        # identity — frontmatter only
├── decision.md   # the decision record — prose only (once decided)
└── research*.md  # optional — written by /research; not read by any skill yet
```

## Why two files

Identity and content are separate so that a generic container skill can open any container without knowing an artifact's content schema — the same pattern as `change.md` + `plan.md` and `effort.md` + `prd.md`. The split also lets a container exist before its decision: a folder at `status: new` has no `decision.md` yet, which is valid, not broken. That state exists so research or notes can land ahead of the session that records the decision.

## Status

`adr.md` carries a four-value status ladder:

| Status | Meaning |
| --- | --- |
| `new` | Container opened; no decision recorded yet |
| `open` | Decided, not yet implemented |
| `done` | Implemented |
| `superseded` | Was implemented; a later ADR changed the decision |

`new` is the exception — it marks a container staked out ahead of its decision. The ladder tracks implementation state, not decision state.

## Skills

Two skills, one container:

- **`/new-container adr <adr-id>`** — opens `context/adrs/<adr-id>/` and writes `adr.md` with `status: new`. Refuses if the id already names a container of any kind. Does not write `decision.md`.
- **`/create-adr [adr-id] [topic]`** — runs a decision session (proposes alternatives, names tradeoffs, recommends, pushes back), then writes `decision.md` and advances `adr.md` to `status: open`. Creates the container when absent; preserves an existing `created` date when reusing one.

Container ids are unique across `context/{changes,efforts,adrs,duck-sessions}/` and `context/archive/` — no two containers of any kind share an id.

## Contract

The authoritative schema lives in the skill references — do not restate it here:

- `references/adr-schema/adr-schema.md` — container layout, `adr.md` frontmatter, status ladder. This is the editable home; consumers cite the materialized copy at `skills/create-adr/references/adr-schema.md` (a symlink into the pack).
- `skills/create-adr/references/decision-schema.md` — `decision.md` sections and mutation rules
- `skills/research/references/research-schema.md` — `research*.md` frontmatter, sections, and filename grammar (optional artifact; no consumer reads it yet)
