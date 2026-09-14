---
status: closed
created: 2026-09-14
updated: 2026-09-14
---

## Boundaries

In scope:

- The effort's outcome: the author's Weles instance runs in production on a Mikrus VPS, and both the author and the certification reviewer use that deployed instance through the TUI.
- Getting the TUI into the hands of anyone who wants it, not only people with GitHub credentials.
- How changes reach `main` and how a change gets verified before it may reach the hosted instance. Once this effort lands, work moves to branches, and `main` accepts changes only through verified pull requests.
- Noticing unhandled errors on the hosted instance.
- Bringing the hosted instance's database (Neon) to the schema the deployed code expects.
- Diagnosing a broken hosted instance with the help of an agent, which observes the instance and recommends what the author should do.
- The constraints the `auth-flow` frame hands to this effort (`context/efforts/auth-flow/frame.md`, Boundaries). The hosted instance is not reachable at a public address before auth-flow FR-01 and FR-05 hold. Its address is hard to discover: it cannot be derived by enumerating a shared-domain naming pattern, and it does not surface through public certificate logs. The public repository, including deployment and CI configuration and agent skills committed to it, names no particular instance (auth-flow FR-07). Choosing the address mechanism is left to planning, within this constraint.
- Sequencing: only the public address waits for auth-flow. CI, TUI publishing, the deployable backend, error reporting, database setup, and diagnostics may all land before auth-flow's data separation is complete.

Out of scope:

- Identity, sign-in, and per-person data separation. These belong to `auth-flow`.
- Sending the content people write (captures, notes, cards) anywhere outside the instance for observability purposes.
- Structured application logging of decision paths beyond error reporting. Deferred: the existing Langfuse tracing of LLM and outbox paths is enough for now.
- Edge protection against flooding (DDoS), which the `auth-flow` frame handed to this effort. Deliberately deferred for an application this small: the hard-to-discover address and auth-flow's attempt limits are the accepted protection for now. Those limits cover sign-in and registration attempts only, not general traffic.
- Running only the suites a pull request touches. Every blocking suite runs on every pull request.
- A publicly pullable backend image, or any release of the backend for others to run their own instances (for example on Docker Hub). The deployable backend serves the author's hosted instance only.
- Moving existing data from a local database into Neon.
- Guarding against deploying a commit whose expected schema differs from the one in Neon. Running the schema script and deploying in the right order is the author's responsibility for now. Revisit before the next schema migration after this effort lands.
- An agent changing anything on the hosted instance: restarting, redeploying, editing configuration, or touching data.

## Requirements

Minted as `FR-nn`: this frame runs on the effort ahead of `/prd`, and no `AC-nn` exists yet to cite.

- **FR-01** — The hosted instance changes only when a person deliberately asks for a specific commit from `main` to be deployed. Nothing about the hosted instance changes merely because a commit lands on `main`.
- **FR-02** — Anyone can install the published TUI without holding GitHub credentials or any other access token.
- **FR-03** — A change reaches `main` only through a pull request whose blocking checks passed. The backend and TUI unit suites and the BDD acceptance suite are blocking checks, and they run on every pull request whatever it touches.
- **FR-04** — Property-based hunts run automatically on every pull request, and their results are visible on it. A failed hunt never blocks a merge.
- **FR-05** — The integration suite, including its Postgres lane, can be run in CI on demand for any commit. It does not run on its own.
- **FR-06** — A commit cannot be deployed to the hosted instance unless its blocking checks passed and an integration run for that same commit, Postgres lane included, passed.
- **FR-07** — An unhandled error on the hosted instance is reported to error tracking without the author having to watch the instance. Error reports and logs never carry the content people write: captures, notes, or cards.
- **FR-08** — The author can bring the hosted instance's Neon database, empty or behind, to the schema a given commit expects by running one supported script.
- **FR-09** — An agent skill can reach the hosted instance, gather what is needed to diagnose it, and report to the author the steps it recommends. While doing so it changes nothing on the instance.
