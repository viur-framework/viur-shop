---
status: proposed
date: 2026-10-23
decision-makers: Sven Eberth
---

# Record architectural decisions as Markdown ADRs (MADR)

## Context and Problem Statement

viur-shop has accumulated design decisions that look like gaps or bugs to anyone who
does not know their history: a fetch limit of 100, discounts sent to Unzer in a
non-obvious shape, notes stored on the cart instead of in the session, return handlers
without an ownership check. The reasoning lives in pull request descriptions, issue
threads and the heads of the maintainers. Contributors — human or AI agents — keep
"fixing" these decisions, and re-deriving the reasoning costs a full investigation each
time.

Where should the reasoning behind such decisions live, so that it is found before
someone changes the code?

## Decision Drivers

* The reasoning must sit next to the code, versioned and reviewed with it.
* It must be findable by contributors and by coding agents, which only see the
  repository.
* It must record *why* and *why not*, not just *what* — the code already shows what.
* Low ceremony: writing a record must not cost more than the PR description it replaces.

## Considered Options

* Architecture Decision Records in MADR format under `docs/decisions/`
* Michael Nygard's original ADR format
* Rely on PR descriptions and code comments
* Per-module reference documentation (one living document per module)

## Decision Outcome

Chosen option: "MADR under `docs/decisions/`", because it is the most widely used
Markdown ADR template, keeps the options and their trade-offs explicit, and carries its
metadata (status, date) in YAML front matter that tools and agents can read.

Conventions:

* One file per decision: `docs/decisions/NNNN-title-with-dashes.md`, numbered
  sequentially. The number is never reused.
* The template is `docs/decisions/adr-template.md` (MADR 4.0.0). Optional sections may
  be dropped.
* `status` is one of `proposed`, `accepted`, `rejected`, `deprecated`,
  `superseded by ADR-NNNN`.
* An accepted ADR is not rewritten. When a decision changes, a new ADR supersedes it,
  and only the `status` of the old one is changed. Typos and links may be fixed.
* `docs/decisions/README.md` lists all ADRs with their status.
* A pull request that makes an architecturally significant decision adds the ADR in the
  same pull request.

### Consequences

* Good, because the "why" survives the PR it was written in and is found where the code
  lives.
* Good, because coding agents get a pointer from `AGENTS.md` and can check a planned
  change against existing decisions.
* Bad, because records written after the fact can only reconstruct the reasoning from
  PRs and discussions; where a reason was not stated, the ADR has to say so instead of
  inventing one.
* Bad, because an ADR describes intent, not behavior — the code can drift away from it.
  The code stays the authority on what actually happens.

## Pros and Cons of the Options

### Nygard format

* Good, because it is minimal (Context, Decision, Status, Consequences).
* Bad, because it has no place for the rejected options, which are exactly what keeps
  a decision from being undone.

### PR descriptions and code comments

* Good, because they already exist for most decisions here.
* Bad, because PRs are not found from the code, and comments only cover one location
  while most of these decisions span several modules.

### Per-module reference documentation

* Good, because it describes the current state of a module in one place.
* Bad, because it has to be rewritten with every change and does not keep the history
  of a decision. It answers "how does it work", not "why was it chosen".

## More Information

* MADR: <https://adr.github.io/madr/>
* Michael Nygard, "Documenting Architecture Decisions" (2011):
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
* ADRs 0001–0019 were written in October 2026 from merged pull requests and the
  discussions around them. Each one links its sources.
