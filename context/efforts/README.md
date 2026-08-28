# Efforts

Multi-change efforts. One folder per effort at `context/efforts/<effort-id>/`, identified by an `effort.md` identity file. Created via `/new-effort`.

## Layout

```
context/efforts/<effort-id>/
├── effort.md      # thin identity + status (created by /new-effort; Goal filled by /prd)
├── prd.md         # feature PRD — product source of truth for this feature (written by /prd)
├── stories.md     # user stories US-nn with acceptance criteria AC-nn (written by /user-stories)
├── frame.md       # optional — /frame <effort-id>
├── research.md    # optional — /research <effort-id>
└── roadmap.md     # optional — /roadmap <effort-id>
```

Run `/user-stories` after `/prd` to write `stories.md` before `/roadmap`.

`prd.md` is the feature's product source of truth. Run `/new-effort` to create the container, then `/prd` to write the PRD.

Effort folders persist in `context/efforts/` when child changes archive — they are reference containers; completed child changes live under `context/archive/`.
