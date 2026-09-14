# TUI Publish Implementation Plan

## Overview

Make the Weles TUI installable by anyone without GitHub credentials or any other access token (deployment FR-02). A tag-triggered workflow builds the TUI, packs it into an npm tarball, and attaches it to a GitHub Release of the public repository. Anyone installs it with `npm i -g <release-asset-url>`.

Execution state lives in `todos.md`, sibling of this file.

## Current State Analysis

- `tui/package.json` is `"private": true`, named `tui`, and has **no `version`**, so `pnpm pack` fails with `ERR_PNPM_PACKAGE_VERSION_NOT_FOUND`.
- `tui/dist/` is gitignored (`.gitignore:8`) and `package.json` has no `files` list, so the packed contents are not pinned to the build output.
- `tui/src/cli.tsx` tells a non-TTY caller to run `pnpm --dir tui build && pnpm --dir tui start` in Cursor, which only makes sense inside a source checkout.
- `.github/workflows/pr-gate.yml` is the only workflow. It pins `actions/checkout@v6` and `pnpm/setup@v2.1.0` (`runtime: node@22`, lockfile cache). No release workflow exists and the repository has no tags.
- GitHub Packages' npm registry requires a token even to install public packages (frame-log `tui-registry-auth`), which rules it out.

## Desired End State

Pushing a tag `tui-v<version>` whose version matches `tui/package.json` produces a GitHub Release carrying `weles-<version>.tgz` and `weles.tgz`. On a machine with Node 22 and no GitHub credentials, `npm i -g https://github.com/web-lizzard/weles/releases/latest/download/weles.tgz` installs a `weles` binary whose `--version` prints the tagged version. The README documents that command.

### Key Discoveries:

- Verified in a scratch copy: with `name: "weles"`, `version: "0.1.0"` and `files: ["dist"]`, `pnpm pack` produces a tarball holding only `package/dist/cli.js` and `package/package.json`. `npm i -g --prefix <tmp> ./weles-0.1.0.tgz` installs its runtime dependencies from the public npm registry, and `weles --help` and `weles --version` (`0.1.0`, read by meow from `package.json`) both work.
- `"private": true` does not block `pnpm pack`. Keeping it prevents an accidental `npm publish`.
- tsup bundles `src/cli.tsx` to `dist/cli.js` with the shebang preserved (`tui/tsup.config.ts`). Dependencies stay external and resolve from `dependencies` at install time.
- Workflow style to follow: `pr-gate.yml` (exact-pinned action refs, `working-directory: tui`, `timeout-minutes`).

## What We're NOT Doing

- Publishing to npmjs.org or GitHub Packages.
- Automated versioning (changesets, semantic-release) or changelog generation. The author bumps `version` and pushes the tag by hand.
- Releasing or publishing the backend.
- Signing tarballs or build provenance attestations.
- Installing directly from a git URL. npm cannot install a package from a repository subdirectory, and `dist/` is not committed.

## Implementation Approach

Phase 1 makes the package packable and installable locally, independent of CI. Phase 2 automates the pack on a tag and publishes the artifact as a GitHub Release asset. Release assets of a public repository download anonymously, which satisfies FR-02 without any registry account. The release also carries a constant-named copy (`weles.tgz`), so the README can use the stable `releases/latest/download/` URL.

## Critical Implementation Details

`releases/latest` resolves to the newest non-prerelease release in the whole repository. It stays correct only while TUI releases are the repository's only releases. If backend releases ever appear, the README must switch to a versioned URL.

## Phase 1: Installable TUI Package

### Overview

Give the TUI package the metadata `pnpm pack` needs and make the packed artifact self-contained and sensible for someone who installed it rather than cloned it.

### Changes Required:

#### 1. Package metadata

**File**: `tui/package.json`

**Intent**: Let `pnpm pack` produce a tarball named after the product that contains exactly the build output.

**Contract**: `name: "weles"`, `version: "0.1.0"`, `files: ["dist"]`. `private: true`, `bin.weles`, `engines.node` and `type: "module"` stay unchanged.

#### 2. Non-TTY guidance

**File**: `tui/src/cli.tsx`

**Intent**: An installed user who launches `weles` without a TTY gets guidance that does not assume a source checkout or a particular editor.

**Contract**: The non-TTY branch still prints to stderr and exits 1. The message says the TUI needs an interactive terminal and to run `weles` from one. It no longer mentions `pnpm --dir tui` or Cursor.

### Success Criteria:

#### Automated Verification:

- `cd tui && pnpm typecheck && pnpm test && pnpm lint` pass
- `cd tui && pnpm build && pnpm pack` succeeds and the tarball lists `package/dist/cli.js`

#### Manual Verification:

- `npm i -g --prefix "$(mktemp -d)" ./tui/weles-0.1.0.tgz`, then `<prefix>/bin/weles --version` prints `0.1.0` and `<prefix>/bin/weles --help` prints the usage

---

## Phase 2: Release Workflow and Install Docs

### Overview

Build and attach the tarball to a GitHub Release whenever the author pushes a `tui-v*` tag, and document the credential-free install.

### Changes Required:

#### 1. Release workflow

**File**: `.github/workflows/tui-release.yml`

**Intent**: Turn a deliberate version tag into a downloadable, anonymously installable TUI artifact. Refuse a tag that disagrees with the package version or whose TUI checks fail.

**Contract**: Trigger `on: push: tags: ["tui-v*"]`. `permissions: contents: write`. A single job with `working-directory: tui` using the same pinned `actions/checkout@v6` and `pnpm/setup@v2.1.0` configuration as `pr-gate.yml`. Steps in order:

1. Fail unless `${GITHUB_REF_NAME#tui-v}` equals `node -p "require('./package.json').version"`.
2. Run `pnpm typecheck` and `pnpm test`.
3. Run `pnpm build`, then `pnpm pack`.
4. Copy the tarball to `weles.tgz`.
5. Run `gh release create "$GITHUB_REF_NAME" weles-<version>.tgz weles.tgz --title "$GITHUB_REF_NAME" --generate-notes` with `GH_TOKEN: ${{ github.token }}`.

#### 2. Install documentation

**File**: `README.md`

**Intent**: Tell a reviewer or self-hoster how to install and point the TUI at an instance with no credentials.

**Contract**: A "Install the TUI" section covering:

- the Node 22 prerequisite
- `npm i -g https://github.com/web-lizzard/weles/releases/latest/download/weles.tgz`
- `weles instance set <address>`
- a one-line release recipe for the author: bump `tui/package.json` `version`, then push tag `tui-v<version>`

### Success Criteria:

#### Automated Verification:

- `actionlint .github/workflows/tui-release.yml` reports no errors

#### Manual Verification:

- Push tag `tui-v0.1.0`. The `tui-release` run succeeds and the release shows `weles-0.1.0.tgz` and `weles.tgz`
- In a clean container with no `GITHUB_TOKEN` and no `.npmrc` (e.g. `docker run --rm -it node:22 sh`), run `npm i -g https://github.com/web-lizzard/weles/releases/latest/download/weles.tgz && weles --version`. It prints `0.1.0`

---

## Testing Strategy

### Unit Tests:

None added. Neither phase changes behaviour a unit test can pin. The existing TUI suite must stay green.

### Integration Tests:

None. The release run itself is the integration check.

### Manual Testing Steps:

1. Local tarball install into a temporary prefix (Phase 1).
2. Tag push, then an anonymous install from the release URL in a clean Node 22 container (Phase 2).

## Performance Considerations

None.

## Migration Notes

The package rename from `tui` to `weles` does not affect `pnpm --dir tui` scripts or the `pr-gate.yml` jobs, which address the directory, not the package name.

## References

- Slice: `context/efforts/deployment/roadmap.md` S-03
- Requirement: `context/efforts/deployment/frame.md` FR-02
- Registry constraint: `context/efforts/deployment/frame-log.md` `tui-registry-auth`
- Workflow pattern: `.github/workflows/pr-gate.yml`
