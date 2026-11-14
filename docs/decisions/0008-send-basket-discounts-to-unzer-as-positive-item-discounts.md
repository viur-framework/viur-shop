---
status: accepted
date: 2026-09-02
decision-makers: Sven Eberth
---

# Send basket discounts to Unzer as positive per-item discounts, split in whole cents

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #202 (problem, `spread_discount`, frozen discount, sandbox measurements).
> - [MEM] v1/v3 basket measurements; Unzer pages show undiscounted gross (also in unzer-python-sdk `AGENTS.md`).
> - [DERIVED] No statement of Sven found on this decision. Option 3 (leave the discount out) is invented.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

A basket-domain discount was sent to Unzer as its own line item (`kind="voucher"`) with
negative amounts — the obvious shape, with the item grosses adding up to the order
total. Both Unzer basket schemas refuse negative item amounts (`API.600.200.131`, plus
`API.600.410.018` on v1), so every Klarna and Paylater Installment checkout with a
basket discount failed.

## Considered Options

* A negative voucher line item
* A positive discount field on the items the discount reduces
* Leave the discount out of the basket and only send the reduced total

## Decision Outcome

Chosen option: "positive discount on the items", because it is the only shape both
schemas accept, measured against the sandbox with real authorizes.

* `spread_discount()` sets a positive `amountDiscount` on the items. A node discount is
  split in whole cents: each item gets the floor of its exact share, the remaining cents
  go one each to the items with the largest fractional part. The parts add up exactly,
  which v3 checks to the cent.
* Weights are what is left of an item after discounts of nested nodes, so no item goes
  below zero. A discount larger than the basket raises instead of building a wrong
  basket.
* `build_node_items()` mirrors `CartNodeSkel.total_discount_price` per node: the
  discount applies to the subtree, the node's own shipping is added afterwards,
  undiscounted.
* The discount *amount* is the difference between the items and the node's stored
  `total_discount_price`, and `has_basket_discount()` reads the frozen discount
  (ADR-0002) — the discount entity may have been deleted or re-scoped since the order
  was placed. The frozen relation stores `application_domain` as a plain string, so it
  has to be normalized before comparing with `ApplicationDomain`.

### Consequences

* Good, because BNPL methods work with basket discounts.
* Good, because the basket reconciles with what the customer is charged even if the
  discount changed later.
* Bad, because Unzer's hosted pages show the item at its undiscounted gross next to a
  lower total; nothing measured displays `amountDiscount`.
* Neutral: the shop sends v1 baskets. v1 does not check its own arithmetic, v3 does.
  Switching to v3 means switching basket *and* items together — a v3 item in a v1 basket
  is stored with all amounts `0` and no error.

## More Information

* #202
* `src/viur/shop/payment_providers/unzer_abstract.py` (`spread_discount`,
  `build_node_items`, `has_basket_discount`)
* The measurements are kept as sandbox tests in the unzer SDK:
  `tests/sandbox/test_live_api.py::TestBasket` in mausbrand/unzer-python-sdk.
