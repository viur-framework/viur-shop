---
status: accepted
date: 2024-03-05
decision-makers: Sven Eberth
---

# Separate the discount value from its conditions, and combine conditions with `ONE_OF` or `ALL`

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed · **[ASANA]** task boards ·
> **[HIST]** git history of the project the shop was extracted from.
>
> - [ASANA] (kickoff board "Shop", 2023-10-18) Task "Rabatte/Gutscheine/Angebotspreise": "Trennung Rabattwert/Rabattkonfiguration"; value: percentage, absolute, free article, free shipping; configuration: all articles, article groups, code (individual/general), combinable, URL, blacklist/whitelist, minimum order value, period, usability, customer group (all, new, regular).
> - [HIST] The old checkout had two separate mechanisms: discount codes on the cart total (`modules/discountCode.py`, from 2020) and article reductions (`modules/discount.py`). Its `canUse` required all preconditions and *at least one* article scope ("Scope-Conditions, At least ONE of the following MUST be true"). Code logic ported in `33f2d18` (2024-03-05).
> - [CODE] `DiscountSkel` (value, `condition` relation `multiple=True`, `condition_operator` default `ALL`), `DiscountConditionSkel` (`scope_*` bones), `ConditionOperator`, `DiscountType`, `ApplicationDomain`.
> - [DERIVED] That the split replaces the two old mechanisms; options; consequences. Why scopes *within* one condition are all required (instead of "at least one article scope" as before) is not recorded.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Discounts come in many shapes: a percentage or a fixed amount, a free article, free
shipping; applied to the whole basket or to some articles; bound to a code, a period, a
minimum order value, a country, a language or a customer group; combinable with other
discounts or not. The checkout the shop was extracted from had two separate mechanisms
for this — discount codes on the cart total and reductions on articles — each with its
own fields.

## Considered Options

* One discount (*what* it gives) with one or more conditions (*when* it applies)
* One skeleton per kind of discount, each with the fields it needs
* Keep codes and article reductions as separate mechanisms

## Decision Outcome

Chosen option: "a discount with conditions", following the requirement collected before
the first line of code to separate the discount value from its configuration.

* `DiscountSkel` holds the value: `discount_type` (`PERCENTAGE`, `ABSOLUTE`,
  `FREE_ARTICLE`, `FREE_SHIPPING`) and its amount.
* `DiscountConditionSkel` holds one set of scopes (`scope_code`, `scope_date_*`,
  `scope_minimum_order_value`, `scope_country`, `scope_language`,
  `scope_customer_group`, `scope_article`, …) and the `application_domain` (basket or
  article). All applicable scopes of one condition must be fulfilled.
* A discount references several conditions and combines them with
  `condition_operator`: `ALL` (default) or `ONE_OF`. An "either this article or that
  one" rule is therefore expressed as several conditions with `ONE_OF`.

### Consequences

* Good, because one mechanism covers codes, campaigns and automatic discounts.
* Good, because a condition can be reused by several discounts.
* Bad, because a simple discount needs two entities, and the meaning of a discount is
  spread over them.
* Bad, because the evaluation is a scope system of its own (`types/dc_scope.py`) that
  projects extend with their own scopes (ADR-0003).

## More Information

* `src/viur/shop/skeletons/discount.py`, `src/viur/shop/skeletons/discount_condition.py`,
  `src/viur/shop/types/dc_scope.py`, `src/viur/shop/types/enums.py`
* The discount code logic itself (individual codes with sub-codes, universal codes,
  usage limit) was ported almost unchanged from that checkout, where it had been in
  production since 2020 (ADR-0019).
