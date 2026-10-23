---
status: proposed
date: 2026-10-09
decision-makers: Sven Eberth
---

# Mark an individual discount code as used when the order is placed

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

* `src/viur/shop/modules/discount_condition.py` (`mark_discount_used`),
  `src/viur/shop/types/dc_scope.py` (`ScopeCode`)
