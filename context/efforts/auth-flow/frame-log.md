## Current State

Session closed 2026-09-13. Every question the session raised has an answer. The body holds the settled frame: FR-01, FR-03, FR-05, FR-06 and FR-07 active, FR-02 withdrawn, FR-04 parked, plus the boundaries.

Left for downstream, not for this frame:

- **tenancy-reach**: FR-05 spans every capture/distill/remember port and the persistence being built in `db-adapter`. `/prd` has to carry that size honestly. It is a fact about scope, not an open question.
- **sequencing with deployment**: the hosted instance stays off public addresses until FR-01/FR-05 hold, and the address choice must satisfy the discoverability constraint. Both need to reach the `deployment` effort when it is framed or PRD'd.

## Log

### 2026-09-13 — functions-unnamed: What auth must accomplish is not yet enumerated — OPEN

**Why:** The invocation says auth "must fulfil several functions" but names only the audience (owner, public TUI downloaders, a reviewer). Without the outcomes, scope cannot be bounded.

### 2026-09-13 — duplicate-auth-effort: Two auth efforts exist — OPEN

**Why:** `context/efforts/auth/effort.md` and `context/efforts/auth-flow/effort.md` are both empty shells created 2026-09-13; `auth-flow` holds the research. One may be redundant, or they may split scope — needs the user's call before the PRD claims the whole area.

### 2026-09-13 — functions-unnamed: all five outcomes accepted — ACCEPTED

The user accepted all five candidates: keep strangers out of the data, keep strangers from spending LLM budget, let the reviewer in without the owner acting live, allow revocation, and separate data per person.

**Why:** User answer "a, b, c, d, e". Separating the data-access and cost outcomes (FR-01 and FR-02) matters because they fail differently: a read-only leak and a spend leak are separate harms. **Consequence:** written as FR-01..FR-05. **Supersedes:** the 2026-09-13 `functions-unnamed` OPEN entry.

### 2026-09-13 — reviewer-data: reviewer gets a separate space, not the owner's instance — ACCEPTED

**Why:** Choosing (e) settles it: the reviewer's data is theirs alone, and by symmetry the reviewer does not see the owner's data. The archived remember-flow frame (`context/archive/changes/2026-09-10-remember-flow-session-resume/frame-log.md`, `per-user-pinning` REJECTED entry) established that an ownership key on some ports but not others "reads as tenancy while enforcing nothing". So separation has to cover the whole chain. **Consequence:** in-scope boundary on the full chain, plus FR-05. The effort is materially larger than a gate-only auth.

### 2026-09-13 — url-secrecy: keeping the URL out of the TUI is not a security control — OPEN

The user's stated pain: the TUI should not store the app URL, and they don't know how to separate the public code from the private deployment.

**Why raised as a reframe:** The observation (public code, private deployment) and the stated remedy (hide the URL) are being treated as one thing. A URL is an address, not a credential. Every granted user's client necessarily learns it. So FR-01/FR-02 must already hold against someone who knows it, and once they do, a known URL adds no data or cost exposure. What remains may be a legitimate but separate concern: the public artifact should not be coupled to one person's deployment. Today the client hardcodes `http://localhost:8000` (`tui/src/api/client.ts:27-29`), so no production URL is in the repo yet. Awaiting the user's view on which concern actually hurts.

### 2026-09-13 — registration-gate: "reviewer may register" vs keeping strangers out — OPEN

**Why:** Self-registration on a publicly discoverable deployment lets any stranger become a "granted" person, which empties FR-01 and FR-02 of meaning. Whatever "register" means, becoming a person with access has to go through the owner's decision in some form. The shape of that decision is the open question, and the answer is observable to a stranger, so it belongs in this frame.

### 2026-09-13 — url-secrecy: the real concern is DDoS exposure, and the URL cannot be withheld from granted users — ACCEPTED

The user clarified that the pain is publishing the URL invites DDoS, while granting that a user cannot log in without it.

**Why:** The user's own statement concedes that the address is not a secret from anyone granted access. So hiding it cannot be a precondition for FR-01/FR-02, and those must hold for someone who knows it. **Consequence:** the concern splits into `ddos-scope` (what auth owes vs what deployment owes) and `url-out-of-artifact` (hygiene). **Supersedes:** the 2026-09-13 `url-secrecy` OPEN entry.

### 2026-09-13 — ddos-scope: volumetric protection belongs to deployment; cheap rejection belongs to auth — OPEN

**Why:** An identity check runs only after a request has already reached the service, so auth cannot keep a flood off the host. That is an edge concern for the `deployment` effort. What auth does control is what a rejected request costs. Grounding: `context/efforts/deployment/research.md` (Neon free tier: exceeding the compute-hour cap suspends compute until next month; traffic prevents scale-to-zero). If unidentified requests reach the database on their way to rejection, an attacker can exhaust the owner's monthly budget without ever breaking a credential. Candidate outcome: rejection of unidentified requests consumes neither LLM nor database resources.

### 2026-09-13 — url-out-of-artifact: the public artifact does not name the owner's deployment — OPEN

**Why:** This is separable from security and cheap as an outcome. The address reaches a granted person from the owner together with their access, and the public repo and TUI stay address-agnostic. It raises the bar only against casual GitHub scanning, and is recorded as hygiene, not protection. Current state: no production address is in the repo (`tui/src/api/client.ts:27-29` hardcodes localhost).

### 2026-09-13 — ddos-scope: flooding out to deployment; cheap rejection in as FR-06 — ACCEPTED

**Why:** The user answered "ok" to the split. Auth cannot keep traffic off the host, but it controls what a rejected request costs, and on a Neon free tier a DB-touching rejection path lets an attacker suspend the instance for the month (`context/efforts/deployment/research.md`). **Consequence:** out-of-scope line for flooding, FR-06. **Supersedes:** the 2026-09-13 `ddos-scope` OPEN entry.

### 2026-09-13 — self-host: pointing the TUI at another instance is supported, not incidental — ACCEPTED

The user plans to publish the app (e.g. Docker Hub) and run private instances inside a devcontainer as a per-repository note system, and wants a CLI action that configures the address, followed by registration and login.

**Why:** This turns the public artifact from a client of one deployment into a client of any instance. **Consequence:** the Boundaries define "the owner" as the operator of the instance in question, so the existing FR text holds without rewording. FR-07 records address configuration as a supported action. Image publishing goes out to `deployment`. **Supersedes:** the 2026-09-13 `url-out-of-artifact` OPEN entry, now settled as FR-07.

### 2026-09-13 — first-owner-bootstrap: how the owner of a fresh instance comes to exist — OPEN

**Why:** Raised by `self-host`. FR-03 and FR-04 presuppose an owner who grants and revokes, but on a freshly started instance nobody holds that role. If the role is claimed by first registration, an instance reachable before its operator registers can be taken over by whoever gets there first. That is a stranger-observable outcome, so it belongs in the frame, not the plan.

### 2026-09-13 — multi-instance: one person, several instances — OPEN

**Why:** A per-repository devcontainer instance alongside the author's cloud instance means a single person can legitimately hold access to more than one. Whether the TUI addresses one at a time or several concurrently is user-visible, e.g. whether switching repositories forces a new login.

### 2026-09-13 — address-as-gate: configuring the address might be protection enough — OPEN

The user asks whether, since the TUI must be pointed at an address, that suffices without an allowlist.

**Why held open with a counter-argument:** Earlier this session the user stated the address must reach every person who logs in (`url-secrecy` ACCEPTED), and FR-07 was accepted as hygiene rather than protection. An ungated instance turns anyone who learns the address into a granted person. FR-05 still isolates their data, but FR-02 (no LLM spend by strangers) fails, and repeated registrations consume database resources on a Neon free tier (`context/efforts/deployment/research.md`). Dropping the gate is therefore a decision to drop FR-02, not a simplification that keeps it.

### 2026-09-13 — operator-configured-allowlist: access decided in instance configuration — OPEN

The user proposes an email allowlist held in the backend's environment.

**Why promising:** At outcome altitude this means access is decided by the instance operator outside the app, before registration. That resolves `first-owner-bootstrap` as option (a), with no race, and `registration-gate` as option (a), and removes the need for an in-app owner role. **Open consequences:** an email on a list only gates if registration proves control of that email; grant and revoke become configuration changes, and it is unsettled whether their latency satisfies FR-04 for a person already logged in. The environment variable itself is a mechanism for `/plan`, not a frame decision.

### 2026-09-13 — address-as-gate: no registration gate for now; an unexposed hosted address is the accepted protection — ACCEPTED

The user decides that, while the only intended users are themself and a reviewer, the risk is small. It is enough that the hosted address is not exposed anywhere.

**Why:** A proportionate call for a two-person, certificate-driven deployment, and the user's to make. The cost was named before the decision (`address-as-gate` OPEN): without a gate, anyone who learns the address becomes a user. FR-05 still isolates data and FR-06 still keeps unidentified rejections cheap, so the exposure is availability and spend, not a data leak. **Consequence:** FR-02 withdrawn. The hosted address being kept out of every public place moves into scope, and FR-07 is widened to deployment/CI config in the public repo, since that address is now load-bearing. **Supersedes:** the 2026-09-13 `address-as-gate` OPEN entry.

### 2026-09-13 — operator-configured-allowlist: email list in instance configuration — PARKED

**Why:** Deferred by the user, not rejected. It remains the preferred shape if a gate returns, because it also removes the first-registrant race and the in-app owner role. **Revisit when:** a third intended user appears; the hosted address shows up anywhere public; registrations appear that neither the author nor the reviewer made; or the provider spend cap is reached by traffic that is not the author's. The open consequences recorded on 2026-09-13 (proof of email control, revocation latency) travel with it.

### 2026-09-13 — cost-among-granted: LLM spend capped at the provider — ACCEPTED

**Why:** The user has limits set on OpenRouter and considers that sufficient for now. **Consequence:** in-app spend protection is out of scope. Noted trade-off: a cap reached by anyone halts LLM-backed capture/distill for the owner too, since the cap is per provider account, not per person.

### 2026-09-13 — first-owner-bootstrap: no owner role to bootstrap while registration is ungated — PARKED

**Why:** With no gate there is no grant step and nobody who must exist first. The question returns with `operator-configured-allowlist`, which already answers it.

### 2026-09-13 — registration-gate: superseded by the no-gate decision — PARKED

**Why:** The options (named list, approval, owner-created access) all describe a gate, which is deferred. It returns with `operator-configured-allowlist`.

### 2026-09-13 — reviewer-handoff: address reaches the reviewer only via a private submission, after auth and deployment land — ACCEPTED

The user states the certification submission is visible only to the reviewer. No hosted address exists yet, because there is no deployment. The address will be shared once this effort and `deployment` are finished.

**Why:** The one channel that carries the address is private, so the accepted protection (an unexposed address) does not leak through the act of granting access. **Consequence:** a sequencing boundary. The hosted instance must not be publicly reachable before FR-01 and FR-05 hold, since the backend currently has no identity check (`backend/src/main.py`). Recorded in `## Boundaries` as a constraint on the order of work with `deployment`.

### 2026-09-13 — fr-04-hollow: revocation parked with the gate — PARKED

**Why:** User: "fr-04 na razie parkujemy". With open registration a revoked person re-registers, so revocation guarantees nothing until a gate exists. **Consequence:** FR-04 marked parked in the body, with an out-of-scope line. It returns with `operator-configured-allowlist`.

### 2026-09-13 — address-discoverability: hard to discover, not merely unpublished — ACCEPTED

**Why:** The user agreed to record it. The protection accepted in `address-as-gate` holds only if the address cannot be found by other means. A shared-domain pattern such as `serwer-port.wykr.es` is enumerable (`context/efforts/deployment/research.md`, DNS / public URL), and non-wildcard certificates are published in Certificate Transparency logs. **Consequence:** in-scope boundary stating the constraint, with the address choice attributed to `deployment`.

### 2026-09-13 — local-instance-auth: same rules on localhost — ACCEPTED

**Why:** The user agrees and notes it is easy to test. This is consistent with `context/adrs/repo-shape/decision.md` (Consequences), which forbids treating the daemon as trusted for being loopback-only. **Consequence:** in-scope boundary.

### 2026-09-13 — multi-instance: one instance at a time — ACCEPTED

**Why:** The user's call ("jedna instancja na razie"). Several remembered instances stay a possible future. **Consequence:** in-scope boundary for one instance, out-of-scope line for several.

### 2026-09-13 — registration-proof: email confirmation deferred — PARKED

**Why:** The user defers it. With FR-05 isolating data and registration ungated, taking someone's email address yields an empty space, not their data. **Consequence:** out-of-scope line. It returns with `operator-configured-allowlist`, where proof of email control is what makes a list meaningful.

### 2026-09-13 — duplicate-auth-effort: `context/efforts/auth/` is a leftover — ACCEPTED

**Why:** The user confirms. The folder holds only an empty `effort.md` shell from commit 3cf8cb2, and `auth-flow` owns the research and this frame. **Consequence:** the leftover is removed outside this frame's files, and `auth-flow` is the single effort for the area.
