# TUI Publish — Plan Brief

> Full plan: `plan.md`

## What & Why

Anyone, including the certification reviewer, must be able to install the Weles TUI without GitHub credentials or any token (deployment FR-02). GitHub Packages' npm registry needs a token even for public packages, so the TUI ships as a tarball attached to a GitHub Release of the public repository.

## Starting Point

`tui/package.json` is private, named `tui`, and has no `version`, so `pnpm pack` fails. `pr-gate.yml` is the only workflow, and nothing builds a distributable TUI.

## Desired End State

Pushing `tui-v<version>` creates a GitHub Release with `weles-<version>.tgz` and `weles.tgz`. On any machine with Node 22, `npm i -g https://github.com/web-lizzard/weles/releases/latest/download/weles.tgz` installs a working `weles` with no credentials, as documented in the README.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Registry | None; GitHub Release tarball | Anonymous download from a public repo, no npm account or token, and the reviewer runs a prebuilt artifact | Frame / Plan |
| Install from source or git URL | Rejected | npm cannot install from a repo subdirectory, `dist/` is gitignored, and the user would need pnpm plus a build | Plan |
| `private: true` | Kept | `pnpm pack` ignores it, and it guards against an accidental `npm publish` | Plan |
| Package name / packed files | `weles`, `files: ["dist"]` | Tarball holds only the bundled CLI and manifest (verified in a scratch copy) | Plan |
| Release trigger | Manual tag `tui-v*`, version must match `package.json` | Deliberate releases, and the tag namespace leaves room for backend tags | Plan |
| Stable install URL | Constant-named `weles.tgz` + `releases/latest/download/` | README does not change on every release | Plan |
| Repository visibility | Public | Anonymous release downloads require it | Plan (user) |

## Scope

**In scope:** package metadata, installed-user non-TTY message, tag-triggered release workflow, README install section.
**Out of scope:** npmjs.org / GitHub Packages publishing, automated versioning, backend releases, signing and provenance.

## Architecture / Approach

The author bumps `version` and pushes a `tui-v<version>` tag. `tui-release.yml` then runs in order:

1. Checks that the tag matches the package version.
2. Runs typecheck and tests.
3. Runs `pnpm build` and `pnpm pack`.
4. Runs `gh release create` with the versioned and constant-named tarballs.

Installers fetch the release asset over HTTPS, and npm resolves runtime dependencies from the public registry.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Installable TUI Package | `pnpm pack` yields an installable `weles` tarball | Missing runtime file outside `dist/` (ruled out by scratch install) |
| 2. Release Workflow and Install Docs | Tag → GitHub Release with tarballs, README install recipe | `releases/latest` points elsewhere if non-TUI releases appear |

**Prerequisites:** repository `web-lizzard/weles` is public.
**Estimated effort:** under a day.

## Open Risks & Assumptions

- `releases/latest` is repository-wide. Backend releases would require a versioned README URL.
- `gh` is preinstalled on GitHub-hosted Ubuntu runners.

## Success Criteria (Summary)

- A `tui-v0.1.0` tag produces a release with both tarballs.
- An anonymous install from the release URL in a clean `node:22` container runs `weles --version` → `0.1.0`.
