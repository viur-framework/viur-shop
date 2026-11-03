---
status: accepted
date: 2026-10-20
decision-makers: Sven Eberth
---

# Revalidate applied discounts in their own context, drop invalid ones and refuse that checkout attempt

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #235 (problem, `REVALIDATE`, `ScopeCode` opt-out, case table).
> - [SVEN] (session 7d1a6b1f) "ein neuer revalidate kontext klingt gut"; on `ScopeCode`: "alle anderen bedingungen sollen auch bei einem code-rabatt natürlich weiter aktiv sein"; chose "Entfernen + Abbruch"; target "develop (minor)".
> - [DERIVED] Sub-decisions made by Claude in that session, not confirmed separately: hook into `listRootNodes`/`basket_view` instead of `get_available_root_nodes`, once per request, no `except Exception`.
> - [MEM] Frontend has to handle the `400`, otherwise the payment step waits forever.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

A discount was validated exactly once, when it was redeemed. Afterwards the relation sat
on the cart node and was folded into every total without any check, and
`freeze_cart()` wrote the reduced total down permanently. A cart that outlived the
discount's validity — campaign over, minimum order value no longer reached, another
shipping country — kept the reduction. Nothing failed; the price was simply too low.

How should applied discounts be re-checked, and what happens to one that no longer
applies?

## Considered Options

For the check:

* Reuse `DiscountValidationContext.NORMAL`
* A new context `DiscountValidationContext.REVALIDATE`

For the outcome at checkout:

* Remove the discount and refuse this checkout attempt
* Only refuse the checkout, keep the discount on the cart
* Remove the discount silently and continue

## Decision Outcome

Chosen options: "new `REVALIDATE` context" and "remove and refuse".

`NORMAL` does not work for revalidation: `can_apply()` short-circuits automatic
discounts in that context, and `ScopeCode` for an individual code is permanently false
once the code was redeemed (`quantity_used > 0`). Every code-bound discount would be
dropped on the first revalidation.

* `REVALIDATE` is part of the default `DiscountConditionScope.allowed_contexts`, so
  scopes registered by a project take part without a change.
* `ScopeCode` opts out — the redeemed code is not stored on the cart. All *other* scopes
  of a code-bound discount are still checked.
* `checkout_start` revalidates before `freeze_order()`. An invalid discount is removed
  and the request is answered with `400` and the translated
  `viur.shop.error.discount.no_longer_valid`. The next attempt goes through at the full
  price.
* The basket views (`listRootNodes`, `basket_view`) revalidate once per request and
  leave a note on the cart (ADR-0004). Revalidation is not hooked into
  `get_available_root_nodes`, which write paths reach via `is_valid_node`.
* No `except Exception` around revalidation: failing silently would bring the original
  bug back.

"Refuse only" leaves the customer stuck with a discount the frontend would have to
remove. "Remove silently" charges more than the confirmation page showed.

### Consequences

* Good, because a cart can no longer carry an invalid discount into a placed order.
* Good, because project scopes are covered by default.
* Bad, because a project scope that must not be re-checked has to opt out explicitly.
* Bad, because the frontend must handle the `400` of `checkout_start` and show its
  message; otherwise the payment step waits forever.
* Neutral: parallel basket requests may revalidate the same cart twice. The removal is
  idempotent.

## More Information

* #201 (issue), #235 (implementation)
* `src/viur/shop/modules/discount.py` (`revalidate_cart`, `revalidate_session_basket`),
  `src/viur/shop/types/dc_scope.py`
* ADR-0019 proposes storing the redeemed code, which would let `ScopeCode` take part.
