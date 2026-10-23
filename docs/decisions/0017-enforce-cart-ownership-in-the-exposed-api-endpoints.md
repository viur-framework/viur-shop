---
status: proposed
date: 2026-10-09
decision-makers: Sven Eberth
---

# Enforce cart ownership in the exposed API endpoints, with the rule in the cart module

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [SVEN] (session 40fa8ea7) "Warum die prüfung in API?"; "das wäre aber auch wieder breaking für die internen funktionen"; first approved option 2 (`canEdit`), "6 klingt interessant, maybe komplett für viur"; order endpoints: "nur bedingt kritisch".
> - [DERIVED] Claude withdrew option 2 after finding the `Tree.edit` hole; Sven continued without objecting — not an explicit approval of option 1. #228 is open.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Several cart endpoints of the API (`cart_update`, `cart_remove`, `cart_clear`,
`cart_list` with a key, `shipping_list`) accepted any cart key, so one session could
read, rename, clear or delete the cart of another. The cart module already has the rule
— `Cart.is_valid_node()` — but its internal functions are also called on behalf of
other sessions, e.g. `delete_guest_cart` from the session's delete hook.

Where should the ownership check be enforced?

## Considered Options

* The exposed API endpoint calls the module rule (`_ensure_own_cart_node()`)
* Override `canEdit` / `canDelete` on the cart module
* Every module function checks ownership itself
* A `check_access` flag on the module functions
* Public checked functions plus private unchecked variants
* Pass the acting user explicitly to every function

## Decision Outcome

Chosen option: "the exposed endpoint calls the module rule", because the rule stays in
one place and internal callers keep working.

`canEdit` / `canDelete` would open a hole instead of closing one: `Cart` inherits from
`Tree`, whose exposed `edit` and `delete` are gated only by those hooks — allowing them
for the owner would let a guest edit the cart directly, bypassing `is_frozen`, discount
and shipping checks. A check inside every module function breaks the internal callers
that act for another session. Flags and private variants are easy to misuse or break
consumers. An explicit actor is the cleanest option but a large refactor, tracked
separately.

### Consequences

* Good, because a foreign cart key is refused with the same error as an invalid one.
* Bad, because every new exposed endpoint that takes a cart key has to call the check.
* Bad, because admins cannot reach foreign carts through the shop API either, as is
  already the case for the article endpoints.

## More Information

* #228 (open), #227 (explicit actor), #229 (assigning foreign address keys)
* Order and payment endpoints (`order_update`, `checkout_start`, `checkout_order`, the
  provider endpoints) lack an ownership check as well. They are considered less critical
  and are to be handled in a separate change.
