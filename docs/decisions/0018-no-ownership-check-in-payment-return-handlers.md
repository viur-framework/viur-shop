---
status: accepted
date: 2026-10-09
decision-makers: Sven Eberth
---

# Do not check session ownership in the payment return handlers

## Context and Problem Statement

After paying on the provider's page, the customer is redirected to the provider's
`return_handler` with the order key. The handler loads the order without checking that
it belongs to the current session. In a review of ownership checks (ADR-0017) this looks
like the same gap.

## Considered Options

* No ownership check in the return handler
* Require the order to belong to the current session

## Decision Outcome

Chosen option: "no ownership check", because the redirect may end in another browser or
app than the one that started the checkout — a banking app, a second device — and the
customer's flow must not fail there.

What makes this acceptable:

* The handler only asks the provider for the payment state; it sets `is_paid` only when
  the provider reports the order as paid.
* Order keys are not sequential and cannot practically be guessed.

### Consequences

* Good, because a payment completed in another browser still completes the order.
* Bad, because anyone who has the order key can trigger a payment check for it. The
  check has no effect beyond what the provider reports.
* Rule: a return handler must never accept a payment state from the request; it reads
  it from the provider.

## More Information

* `src/viur/shop/payment_providers/unzer_abstract.py` (`return_handler`),
  `src/viur/shop/payment_providers/unzer_openbanking_pis.py`
