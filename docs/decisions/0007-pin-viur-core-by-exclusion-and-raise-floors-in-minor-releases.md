---
status: accepted
date: 2026-10-20
decision-makers: Sven Eberth
---

# Exclude broken viur-core releases individually; raising a dependency floor is a breaking change

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #235, #233 (pins, breaking change).
> - [SVEN] (session 7d1a6b1f) "prüfe ob es wirklich 3.8.41 braucht, oder ob einfach nur 3.8.40 buggy war"; (6ad34875) "der core version change in #233 ist IMO eig ein breaking change". No version bump in PRs: Sven 2026-09-09 (memory).
> - [DERIVED] Phrasing as two general rules; consequence about merging `main` into `develop`.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

viur-shop runs inside projects that pin their own viur-core. Two situations recur:

* A viur-core release is broken for the shop. viur-core #1788 (3.8.40, 3.9.1, 3.9.2)
  made parallel cart reads return `None` for computed totals; 3.8.41 / 3.9.3 fixed it.
* The shop starts using a core API that older releases do not have (`computing()`,
  see ADR-0006).

How should the dependency range express this, and in which release does a change of the
range belong?

## Considered Options

* Exclude the broken releases with `!=` and keep the floor
* Raise the floor past the broken releases
* Raise the floor in a patch release on `main`
* Raise the floor in a minor release on `develop`, marked as breaking

## Decision Outcome

Chosen options: "exclude with `!=`" for broken releases, and "raise the floor only in a
minor release, marked as breaking" when the shop needs a newer API.

Raising the floor to skip a broken release locks out every working release below it
for no reason — measured, 3.8.39 works, only 3.8.40 is broken. A higher floor forces
every project to upgrade its core before it can take a shop fix, so it is a breaking
change: commit type `fix!`/`feat!` with a `BREAKING CHANGE` footer, target `develop`.

### Consequences

* Good, because projects on a working older core keep receiving patch releases.
* Good, because a floor change is visible in the changelog as breaking.
* Bad, because the `!=` list grows and has to be kept in mind when the floor is raised
  later. When the floor passes an excluded release, the exclusion is dropped.
* Bad, because `main` and `develop` can carry different ranges. A merge from `main`
  into `develop` has to keep the stricter line.

## More Information

* #235 (`viur-core>=3.7.0,!=3.8.40,!=3.9.1,!=3.9.2` on `main`),
  #233 (`viur-core>=3.8.41,!=3.9.0,!=3.9.1,!=3.9.2` on `develop`)
* The shop's own version is not bumped in feature or fix pull requests; it is set in a
  separate `chore: bump version to vX.Y.Z` commit at release time. Dependency pins
  belong in the pull request that needs them.
