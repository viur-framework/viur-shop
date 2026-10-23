---
status: accepted
date: 2024-03-07
decision-makers: Sven Eberth
---

# Compute prices as floats rounded to cents, until a switch to `Decimal` is decided

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed · **[ASANA]** viur-shop task board.
>
> - [ASANA] (task "Preis-Variablen als Decimals statt Floats deklarieren", open) A request to store prices as `Decimal` to avoid rounding errors. [SVEN] comment 2026-03-30: "Hätte ich vor zwei Jahren auch gerne so implementiert. Kann ViUR aber nicht." with links to viur-core#1099 and the `TODO` in `types/price.py`. Later comments: prioritized in the core, "wird wahrscheinlich in ViUR Core 3.9 gelöst".
> - [CODE] `types/price.py` (`float` properties, `PRICE_PRECISION`, `toolkit.round_decimal`, the `TODO`); viur-core#1099 closed 2026-07-28; `NumericBone(decimal=...)` added in viur-core #1666, contained in the tags v3.8.41 and v3.9.0 (`git tag --contains`).
> - [SVEN] (this conversation) viur-shop was developed against viur-core 3.6 dev, and many 3.6 changes came from its requirements; the float decision is two years old, the 3.8.41 floor three days. Changing this in production is a breaking change that needs capacity; stability and requested features came first.
> - [CODE] First shop commit 2023-12-12, `Price` with `float` properties since 2024-03-07; viur-core v3.6.0 tagged 2024-03-21; first explicit core floor `>=3.7` on 2025-03-14 (#102); `>=3.8.41` since 2026-10-20 (#233); viur-core #1666 merged 2026-06-29.
> - [HIST] (git history of the project the shop was extracted from, verified by Claude) prices were already floats rounded with `round_decimal` in the checkout the shop was extracted from (2020–2023).
> - [DERIVED] Options and consequences. Whether the shop *should* switch is not decided.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Prices, totals, VAT and discounts are computed in `Price` (`types/price.py`) and stored in
`NumericBone`s. Binary floating point cannot represent most cent amounts exactly, so sums
and differences pick up tiny errors (`12.3 - 10.0 - 2.3` is `8.88e-16`, not `0`), which
then need rounding before they are shown, stored or sent to a payment provider.

The checkout the shop was extracted from already computed prices as floats rounded to
cents. `decimal.Decimal` would avoid the errors. But when the shop was written — from December 2023,
against the development state of viur-core 3.6 (released March 2024) — `NumericBone`
could only store `int` and `float`, and a shop on ViUR had no way to persist a
`Decimal`.

## Considered Options

* Floats, rounded to `PRICE_PRECISION` (2) where a price is produced
* `Decimal` in the computations, converted to float for storage
* Integer cents throughout

## Decision Outcome

Chosen option: "floats, rounded to cents", because it is what `NumericBone` could store,
and computing in another type than the one that is stored would mean converting on every
read and write.

* Every price property of `Price` rounds its result with
  `toolkit.round_decimal(..., PRICE_PRECISION)`.
* Code that sends amounts to an external system rounds again at that boundary — float
  arithmetic between two rounded values can produce a value with more digits.

### Consequences

* Good, because prices are plain numbers in the datastore and in the JSON API.
* Bad, because every new computation has to remember to round, and a missed rounding
  surfaces only at an external boundary (e.g. Unzer refuses amounts with more than four
  decimal places).
* Neutral: the original blocker has gone away only recently. `NumericBone(decimal=True)`
  was merged into viur-core in June 2026 (viur-framework/viur-core#1099, #1666) and is
  contained in 3.8.41 / 3.9.0; viur-shop has required such a core only since
  October 2026, for an unrelated reason (ADR-0006).

### Why it has not changed since

The decision was right for its time, and nothing about it is broken: prices are rounded
and add up. Switching now would change the stored values and the API output of every
project running the shop — a breaking change for production systems that needs a
migration, frontend changes and capacity. Like other refactorings, it stays behind
stability and the features projects ask for, until it is planned as a change of its own
with its own record.

## More Information

* `src/viur/shop/types/price.py` (`PRICE_PRECISION`, the `TODO: Use decimal package
  instead of floats?`)
* viur-framework/viur-core#1099 ("Implement decimal mode in `NumericBone`")
