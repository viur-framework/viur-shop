---
status: accepted
date: 2026-10-15
decision-makers: Sven Eberth
---

# Freeze the cart when the order is placed; frozen values are the record of the order

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #196 (`SnapshotRelationalBone`, trade-off), #202 (basket reads frozen values), #230.
> - [SVEN] (session b9f63b42) "is_frozen in den ref keys macht doch mehr sinn?", "fehlt dann nicht auch frozen_data selbst in den ref keys?"; old orders not migrated (memory: "Svens Entscheidung").
> - [MEM] The cause behind #230 (order viewed from another country lost its shipping); `frozen_values` breaking a consumer's export.
> - [ASANA] (viur-shop board, task "AddressSkel nicht löschbar, wenn Adresse bei Bestellung referenziert, die nicht abgeschlossen wurde", created by Sven, open) "vor freeze nicht geklont, in OrderSkel auf preventDeletion. Lösung: conditional prevent delete" — used for the open point below; [CODE] the `PreventDeletion` named there was not found on the address relation.
> - [DERIVED] Framing "frozen values are the record of the order"; options 2 and 3 (separate total, plain copy) were never discussed — invented as contrast.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Cart totals, shipping, discounts and VAT are computed bones (`ComputeMethod.Always`):
they are recomputed on every read from the current articles, discounts, shipping
configuration and request (country, language). That is right while the customer shops,
and wrong after the order is placed — the customer was charged a specific amount, and a
later price change, deleted discount or a request from another country must not change
what the order says.

Addresses have the same problem in a relation: an order keeps a copy of the billing and
shipping address, and that copy must follow edits during the checkout but not after it.

## Considered Options

* Freeze: copy the computed values into `frozen_values`, set `is_frozen`, and stop
  recomputing from then on
* Keep recomputing and store a separate order total only
* Copy the whole cart into the order as a plain record

## Decision Outcome

Chosen option: "freeze", because the cart structure stays one data model for open and
placed orders, and everything that reads a cart (templates, exports, payment providers)
can use the same fields.

Rules that follow from it:

* `Cart.freeze_cart()` writes `frozen_values` (totals, VAT, shipping, discount,
  shipping address) and `is_frozen` on every node and leaf, without a fetch limit.
* Computed bones check `is_frozen` first and return the frozen value.
* Readers that must reproduce what the customer was charged read `frozen_values`,
  not the live relation. The Unzer basket does so for the discount (see ADR-0008),
  because the discount entity may have been deleted or re-scoped since.
* `is_frozen` and `frozen_values` are part of the `refKeys` of `OrderSkel.cart`. Without
  them, the order's copy of the cart looks unfrozen and its computed bones are
  recomputed with the *current* request — an order viewed from another country lost its
  shipping.
* Address copies use `SnapshotRelationalBone`: `updateLevel=Always` while the owner is
  open, `refresh()` becomes a no-op once it is frozen. Neither static `updateLevel` fits:
  `Always` changes placed orders retroactively, `OnValueAssignment` misses edits made
  in later checkout steps.

### Consequences

* Good, because a placed order is stable against later changes of articles, discounts,
  shipping and the request context.
* Bad, because every computed bone and every reader has to respect `is_frozen`. A new
  computed bone that forgets the check silently recomputes placed orders.
* Bad, because orders written before the `refKeys` fix only benefit once their relation
  is rewritten (e.g. by saving them). They were deliberately not migrated.
* Bad, because `frozen_values` contains serialized keys and nested structures; consumers
  that export it verbatim have to handle that.
* Neutral: editing an address referenced by a frozen order still triggers one
  `update_relations` write of that order, which changes nothing. Avoiding it would need
  a dynamic `updateLevel` in viur-core.

## More Information

* Open: an address referenced by an order that was never completed cannot be deleted.
  Proposed: prevent the deletion only while it matters (conditional). Which mechanism
  blocks the deletion today is not identified: `OrderSkel.billing_address` sets no
  `consistency`, `PreventDeletion` sits on `OrderSkel.cart`.
* #196 (`SnapshotRelationalBone`), #202 (Unzer basket reads frozen values),
  #230 (`refKeys` of `OrderSkel.cart`)
* `src/viur/shop/modules/cart.py` (`freeze_cart`, `freeze_leaf`),
  `src/viur/shop/skeletons/_bones.py`
