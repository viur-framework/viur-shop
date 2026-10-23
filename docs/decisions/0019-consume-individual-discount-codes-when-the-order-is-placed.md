---
status: proposed
date: 2026-10-09
decision-makers: Sven Eberth
---

# Mark an individual discount code as used when the order is placed

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [SVEN] (session 40fa8ea7) "code bei ordered order hochzählen" — the trigger only.
> - [CODE] `mark_discount_used`, `ScopeCode`.
> - [HIST] (git history of the project the shop was extracted from, verified by Claude) the discount code logic, including sub-codes, was ported almost 1:1 into viur-shop (`33f2d18`, 2024-03-05; Sven: "fast 1:1 übernommen", well proven in production). The old code incremented usage after payment (`processDiscountCode` from `setRTS`) and stored the applied code with its value on the order.
> - [DERIVED] Everything under "Not decided yet" is Claude's plan, not approved; the consequence about two carts.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

A discount condition with `CodeType.INDIVIDUAL` has one sub-code per customer.
`mark_discount_used` only increments the parent condition, and `ScopeCode` checks
`quantity_used` on whichever sub-code it finds first. The code a customer redeemed is
not stored on the cart. So an individual code is never actually used up, and
revalidation cannot check it either (ADR-0003).

## Considered Options

* Increment the redeemed sub-code when the order is placed (`ORDER_ORDERED`)
* Increment it when the code is applied to the cart

## Decision Outcome

Chosen option: "when the order is placed", because applying a code to a cart that is
then abandoned would use it up without an order.

Not decided yet:

* where the redeemed code is stored (proposal: a `discount_code` bone on
  `CartNodeSkel`), so that exactly that sub-code is incremented and `ScopeCode` checks
  exactly the entered code;
* whether `ScopeCode` then takes part in revalidation;
* the target branch — a new bone is a data model change.

### Consequences

* Good, because an individual code can be redeemed once, as its name says.
* Bad, because two carts can redeem the same code until one of them is ordered.

## More Information

* The discount code logic was ported almost unchanged from the production checkout the
  shop was extracted from, where it had been in use since 2020. That checkout stored the
  redeemed code on the order and counted it after payment.
* `src/viur/shop/modules/discount_condition.py` (`mark_discount_used`),
  `src/viur/shop/types/dc_scope.py` (`ScopeCode`)
