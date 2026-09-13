---
status: closed
created: 2026-09-13
updated: 2026-09-13
---

## Boundaries

In scope:

- Access to any running instance of the Weles backend. The source repository and the published artifacts are public. Each running instance belongs to whoever operates it: the author's cloud deployment, or someone's own instance, for example one run inside a devcontainer as a private note system for a single repository. Throughout the requirements, "the owner" means the operator of the instance in question.
- Pointing the TUI at an instance chosen by the person using it, as a supported use rather than an incidental one.
- Every person who uses an instance, the owner and a certification reviewer included, as an identified individual with their own data.
- The whole capture → distill → remember chain. Data separation between people covers every stage, not only a subset of them.
- What a rejected, unidentified request costs the instance.
- The same identity rules on every instance, including a local devcontainer instance on localhost. No instance is trusted because of where it runs (`context/adrs/repo-shape/decision.md`, Consequences).
- The TUI is pointed at one instance at a time. Pointing it at a different instance replaces the previous one.
- While registration is ungated, "granted access" in the requirements means having registered and signed in on that instance.
- Keeping the address of the author's hosted instance out of every public place. For now this is the only thing standing between strangers and self-registration on that instance.
- The author's hosted instance is not reachable at a public address before FR-01 and FR-05 hold. Today the backend has no identity check at all (`backend/src/main.py`), so this constrains the order of work with the `deployment` effort. The address reaches the reviewer only through the certification submission, which is private to the reviewer.
- The hosted instance's address is hard to discover, not merely unpublished: it cannot be derived by enumerating a shared-domain naming pattern (such as Mikrus `serwer-port.wykr.es`) and does not surface through public certificate logs. This effort states the constraint; choosing the address belongs to the `deployment` effort.

Out of scope:

- Teams, shared workspaces, or any data visible to more than one person. `context/foundation/project-overview.md` keeps Weles a single-person instrument, and a second person gets a second, separate instrument.
- Protection against volumetric flooding (DDoS). An identity check runs only after traffic has reached the service. Keeping a flood off the host is an edge concern for the `deployment` effort.
- An operator-controlled list of who may register, or any other gate on who can become a user of an instance. Deliberately deferred while the only intended users are the author and one reviewer. Revisit triggers are recorded in `frame-log.md` (`operator-configured-allowlist`).
- Revoking a person's access. Parked with the registration gate, because a revoked person could simply register again (see FR-04).
- Proving control of an email address at registration. Parked; with FR-05 isolating data, the stakes are low while registration is ungated.
- A TUI that holds several instances at once, for example one per repository.
- Protecting LLM spend in the application. Spend is capped at the LLM provider (OpenRouter limits). Once that cap is hit, LLM-backed steps stop for every user of the instance, the owner included, and that is accepted.
- Publishing images or packages (GHCR, Docker Hub) and hosting instances. These belong to the `deployment` effort.

## Requirements

Minted as `FR-nn`: this frame runs on the effort ahead of `/prd`, and no `AC-nn` exists yet to cite.

- **FR-01** — A person who has not been granted access cannot read or write any data in the owner's deployment.
- **FR-02** — *Withdrawn 2026-09-13.* Guarding LLM spend against strangers is not required of this effort; spend is capped at the LLM provider (see Boundaries).
- **FR-03** — A person who has been granted access, such as the reviewer, can get in without the owner having to act at that moment.
- **FR-04** — *Parked 2026-09-13.* Revoking access returns together with the registration gate (see Boundaries).
- **FR-05** — A person's captures, notes, cards, and review history are visible only to that person.
- **FR-06** — Rejecting a request from an unidentified caller consumes neither LLM nor database resources of the instance.
- **FR-07** — The public repository and published TUI name no particular instance. A person points the TUI at an instance of their choosing through a supported TUI action, without editing code or rebuilding. This also covers deployment and CI configuration committed to the public repository. FR-01 and FR-06 still hold for a caller who knows the address.
