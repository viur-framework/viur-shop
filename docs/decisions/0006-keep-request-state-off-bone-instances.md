---
status: accepted
date: 2026-10-20
decision-makers: Sven Eberth
---

# Keep request state off bone instances; guard computations per skeleton and thread

## Context and Problem Statement

A bone instance is created once per skeleton class and shared by every skeleton instance
of that class and by every thread of the process. `RelationalBoneShipping` guarded its
recursion with a flag on the bone (`_prevent_compute`). While one request computed the
cheapest shipping, every other request reading a cart in parallel saw the flag and
returned the *stored* shipping instead of computing it — no error, just a possibly
outdated value.

viur-core moved away from the same pattern (viur-framework/viur-core#1793) and
deprecated `_prevent_compute`.

## Considered Options

* Use viur-core's `BaseBone.computing()` / `is_computing()`, keyed by skeleton and thread
* Keep the bone flag on `main`, switch to `computing()` only when available
* Do nothing until the dependency floor rises for another reason

## Decision Outcome

Chosen option: "use `computing()`", because a guard has to be scoped to what it guards.
The recursion runs through the same skeleton, so a per-skeleton guard covers it.

A runtime switch would be code that exists only to be removed later. Waiting is not an
option for a deprecated core API that will be removed.

General rule: **no per-request or per-skeleton state on a bone instance** — not as an
attribute, not as a flag, not as a cache keyed implicitly by "the current" anything.
Such state belongs on the skeleton instance, in `current.request_data`, or in a guard
keyed by skeleton and thread.

### Consequences

* Good, because parallel requests no longer influence each other's shipping.
* Bad, because the dependency floor rises to `viur-core>=3.8.41` (3.9.0–3.9.2 lack
  `computing()`), which is a breaking change (ADR-0007).

## More Information

* #233, viur-framework/viur-core#1792, viur-framework/viur-core#1793
* `src/viur/shop/skeletons/cart.py` (`RelationalBoneShipping`)
