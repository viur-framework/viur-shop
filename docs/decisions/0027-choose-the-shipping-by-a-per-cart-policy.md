---
status: accepted
date: 2025-06-30
decision-makers: Sven Eberth
---

# Choose the cart's shipping by a policy: the customer's choice, the cheapest or the most expensive

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed · **[ASANA]** task boards ·
> **[HIST]** git history of the project the shop was extracted from.
>
> - [SVEN] (this conversation) Projects compute shipping differently from the shop's default; the project the shop was extracted from overrides it.
> - [CODE] `ShippingStatus` (`USER`, `CHEAPEST`, `MOST_EXPENSIVE`), `CartNodeSkel.shipping_status` default `CHEAPEST`, `RelationalBoneShipping.unserialize_compute` (`min`/`max`, user choice kept while valid, frozen carts keep the stored value). `MOST_EXPENSIVE` added in #135 (2025-06-30, no description). A project sets the default to `MOST_EXPENSIVE` and overrides the shipping module.
> - [HIST] The old checkout used the most expensive shipping for the whole cart since 2021-06-18 (`09e564c0f`, "Use max instead of min shipping costs (for the entire cart)"); no reason recorded.
> - [MEM] A project-side default of `MOST_EXPENSIVE` plus a missing persisted relation once left orders without shipping (fixed by #230, ADR-0002).
> - [DERIVED] Options, consequences, the link to ADR-0023.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

A cart usually has several applicable shipping methods. Which one applies differs
between projects: some let the customer choose, some charge the cheapest applicable
method, and the checkout the shop was extracted from deliberately charged the most
expensive method for the whole cart. A single built-in rule would be wrong for some of
them.

## Considered Options

* A policy per cart node (`shipping_status`) with the shop's default and a project-wide
  default that projects can change
* One fixed rule in the shop, projects override the computation
* Always let the customer choose

## Decision Outcome

Chosen option: "a policy per cart node", because the rules that more than one project
needs are general enough to belong in the shop (ADR-0023), and the policy can still be
replaced in a project.

* `ShippingStatus.USER`: the customer's choice is kept as long as it is still valid;
  otherwise the cart falls back to the computed one.
* `ShippingStatus.CHEAPEST` (default) or `MOST_EXPENSIVE`: the shipping is computed from
  the applicable methods on every read (`min` / `max` by `shipping_cost`).
* A frozen cart keeps its stored shipping (ADR-0002).
* A project changes the default of `CartNodeSkel.shipping_status`, and can override the
  shipping module for rules beyond these policies.

### Consequences

* Good, because the common policies are configuration, not project code.
* Bad, because the computed shipping is only persisted when the cart is written; a
  reader that skips `refresh()` sees the computed value, not the stored one
  (ADR-0002).
* Bad, because a reset of a no-longer-valid user choice happens silently in the read
  path; telling the customer is open (#239).

## More Information

* `src/viur/shop/types/enums.py` (`ShippingStatus`), `src/viur/shop/skeletons/cart.py`
  (`RelationalBoneShipping`, `CartNodeSkel.shipping_status`)
* #135 (`MOST_EXPENSIVE`), #233 (computation guard, ADR-0006), #239
