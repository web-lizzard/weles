## Current State

Session closed 2026-09-14. Every question the session raised has an answer or is parked with a recorded trigger. The body holds the settled frame: FR-01..FR-09 plus the boundaries.

Left for downstream, not for this frame:

- **mechanisms for planning**: the TUI registry (GitHub Packages npm needs a token, so FR-02 rules it out), the hard-to-discover address mechanism, the CI Postgres service, and the error-tracking vendor (Sentry was the user's initial pick).
- **revisit trigger**: schema/deploy ordering, before the next schema migration after this effort lands.

## Log

### 2026-09-14 — manual-deploy: deploys happen only on deliberate request for a chosen main commit — ACCEPTED

**Why:** The user stated it explicitly: "manualny job po main wdraża z danego commita — nie auto!". **Consequence:** FR-01.

### 2026-09-14 — inherited-auth-constraints: auth-flow's handed-over constraints bind this effort — ACCEPTED

**Why:** `context/efforts/auth-flow/frame.md` (Boundaries) assigns three things to `deployment`: no public address before FR-01/FR-05 hold, a non-enumerable address that stays out of CT logs, and the flooding concern. `context/efforts/auth-flow/frame-log.md` (Current State, "sequencing with deployment") asks for them to reach this effort's frame. **Consequence:** in-scope boundaries.

### 2026-09-14 — effort-outcome: what the effort is for is unstated — OPEN

**Why:** The input lists mechanisms only. Without the outcome, nothing on the list can be judged required or optional.

### 2026-09-14 — tui-registry-auth: GitHub npm registry requires auth to install — OPEN

**Why:** GitHub Packages' npm registry requires an authenticated token to install packages, public ones included. `tui/package.json` is `"private": true`, name `tui` (unscoped). That clashes with a TUI that a reviewer or self-hoster can simply install (auth-flow AC-01, "published TUI").

### 2026-09-14 — merge-gate-reality: a merge gate without PRs gates nothing — OPEN

**Why:** Recent commits land directly on `main` (git log), and no `.github/` exists. A check that runs after landing is a report, not a gate.

### 2026-09-14 — bdd-integration-manual: manual BDD contradicts testing conventions — OPEN

**Why:** `context/foundation/testing-conventions.md` Stack → BDD says "Blocking: blocking". Only property and mutation are advisory.

### 2026-09-14 — address-vs-wykres: research's wykr.es fast path violates the discoverability constraint — OPEN

**Why:** `research.md` (DNS / public URL) recommends `serwer-port.wykr.es`, which auth-flow's `address-discoverability` ACCEPTED entry names as enumerable.

### 2026-09-14 — effort-outcome: production deployment used by the author and the reviewer — ACCEPTED

**Why:** The user said: "Wdrożenie aplikacji na produkcję to jest cel, ja czy recenzent możemy korzystać z wydeployowanej instancji." **Consequence:** first in-scope boundary. **Supersedes:** the 2026-09-14 `effort-outcome` OPEN entry.

### 2026-09-14 — tui-registry-auth: anyone installs the TUI without credentials; GitHub npm registry cannot deliver that — ACCEPTED

**Why:** The user wants anyone to be able to install, assuming a public GitHub package needs no auth. GitHub docs (Working with the npm registry, Authenticating) contradict that: "You need an access token to publish, install, and delete private, internal, and public packages." The outcome stands and the registry choice goes to planning. **Consequence:** FR-02. **Supersedes:** the 2026-09-14 `tui-registry-auth` OPEN entry.

### 2026-09-14 — merge-gate-reality: main becomes protected, changes arrive via PRs — ACCEPTED

**Why:** The user: "po wdrożeniu tego deploymentu lecimy branche'ami i protected branch na main." **Consequence:** FR-03. **Supersedes:** the 2026-09-14 `merge-gate-reality` OPEN entry.

### 2026-09-14 — bdd-integration-manual: BDD stays blocking; integration on demand; property automatic and non-blocking — ACCEPTED

**Why:** The user agreed BDD stays in the blocking suite. Integration becomes manually triggered. Property hunts run automatically in a separate non-blocking job, to actively search for weak arguments. This matches `testing-conventions.md` (BDD blocking, property advisory). **Consequence:** FR-03, FR-04, FR-05. **Supersedes:** the 2026-09-14 `bdd-integration-manual` OPEN entry.

### 2026-09-14 — deploy-gate-link: red commits are not deployable — ACCEPTED

**Why:** Asked whether a commit with red or unrun checks may be deployed, the user answered "nie wolno". **Consequence:** FR-06. Whether the manual integration lane counts toward that gate is reopened as `integration-vs-deploy-gate`.

### 2026-09-14 — address-vs-wykres: constraint stands, mechanism left to planning — PARKED

**Why:** The user: "to plan ustali, ale fakt dobrze by było coś trudnego do znalezienia." The inherited discoverability boundary already binds the plan. **Supersedes:** the 2026-09-14 `address-vs-wykres` OPEN entry.

### 2026-09-14 — observability-outcome: errors only, no written content leaves the instance — ACCEPTED

**Why:** Asked whether note content may leave the instance in error events, the user answered "nie, raczej na razie tylko błędy". **Consequence:** FR-07 and an out-of-scope line. Key-path logging stays open as `key-path-logging`.

### 2026-09-14 — path-filter-vs-required: path-filtered suites cannot be required checks as-is — OPEN

**Why:** GitHub docs (Troubleshooting required status checks): skipped workflows leave checks "Pending" and "block merging". The TUI API types are generated from the backend schema, so path boundaries leak.

### 2026-09-14 — integration-vs-deploy-gate: Postgres adapters may reach production untested — OPEN

**Why:** Only the integration `-m postgres` lane exercises SQL adapters. It is manual (FR-05) and outside the blocking checks that gate deploys (FR-06).

### 2026-09-14 — path-filter-vs-required: every blocking suite runs on every PR — PARKED

**Why:** The user: "to parkujmy (odpalamy obie suity)". Path-scoped runs are deferred rather than rejected. Required checks skipped by path filters block merging (GitHub docs, Troubleshooting required status checks), and backend changes can break the generated TUI types. **Consequence:** FR-03 amended to run on every PR, plus an out-of-scope line. **Supersedes:** the 2026-09-14 `path-filter-vs-required` OPEN entry.

### 2026-09-14 — integration-vs-deploy-gate: deploy requires a passing integration run with Postgres — ACCEPTED

**Why:** The user: "deploy tak — trzeba zrobić setup serwisu postgres w ci". Production runs on Postgres, and only the `-m postgres` lane exercises the SQL adapters. The CI Postgres service is a mechanism for planning. **Consequence:** FR-06 amended; FR-05 unchanged. **Supersedes:** the 2026-09-14 `integration-vs-deploy-gate` OPEN entry.

### 2026-09-14 — key-path-logging: dropped for now, Langfuse suffices — PARKED

**Why:** The user: it would mean a lot of churn in production code, and Langfuse is enough for now. **Consequence:** out-of-scope line. FR-07 (errors only) stands.

### 2026-09-14 — flooding: deferred; hidden address plus attempt limits accepted — PARKED

**Why:** The user: rate limits and a hidden URL should be enough for an app this small. Note that auth-flow S-07 limits only sign-in and registration attempts (`context/efforts/auth-flow/roadmap.md`, S-07), not general traffic. **Consequence:** the flooding line moves from in-scope-undecided to out of scope, deferred.

### 2026-09-14 — self-host-images: the answer addressed Mikrus deployment, not public pullability — OPEN

**Why:** The user prefers deploying to Mikrus from a container. That settles the runtime shape (a mechanism) but not whether anyone other than the author can pull the backend image.

### 2026-09-14 — db-migrate-meaning: script brings the Neon schema to a commit's version; no data transfer — ACCEPTED

**Why:** The user chose option (a): the script brings the schema to head. Moving local data into Neon was option (b), not chosen. **Consequence:** FR-08 plus an out-of-scope line. How the script relates to deploys stays open as `schema-on-later-deploys`. **Supersedes:** the 2026-09-14 `db-migrate-meaning` thread in Current State (never logged as OPEN).

### 2026-09-14 — diag-skills-exposure: read-only diagnostics that recommend steps — ACCEPTED

**Why:** The user: read-only capabilities only. The skill should communicate with the VPS to diagnose and list recommended steps if something breaks. Read-only keeps agents from bypassing FR-01/FR-06, and the inherited no-address boundary now names agent skills. **Consequence:** FR-09 plus an out-of-scope line for agent write actions.

### 2026-09-14 — self-host-images: public backend image out of scope — ACCEPTED

**Why:** The user: not for now, and a Docker Hub release sits outside this effort. This narrows auth-flow's `self-host` intent for this effort only. auth-flow FR-07, which keeps the repo instance-agnostic, still holds. **Consequence:** out-of-scope line. **Supersedes:** the 2026-09-14 `self-host-images` OPEN entry.

### 2026-09-14 — sequencing: only the public address waits for auth-flow — ACCEPTED

**Why:** The user confirmed the order: the public address waits for auth-flow FR-05 (S-04/S-05 pending in `context/efforts/auth-flow/roadmap.md`), and everything else may land earlier. **Consequence:** in-scope sequencing boundary.

### 2026-09-14 — schema-on-later-deploys: relation between schema script and deploys undecided — OPEN

**Why:** FR-08 makes schema changes a separate script and FR-01 makes deploys manual, so the two can run out of order. The app does not migrate on startup (`backend/src/main.py` lifespan starts only the outbox worker).

### 2026-09-14 — schema-on-later-deploys: ordering left to the author for now — PARKED

**Why:** The user chose (c), leaving it with the author as an accepted risk for a single-operator instance, and suggested revisiting before the next migration. **Consequence:** an out-of-scope line with that revisit trigger. **Supersedes:** the 2026-09-14 `schema-on-later-deploys` OPEN entry.
