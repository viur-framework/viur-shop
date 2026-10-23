---
status: accepted
date: 2026-08-15
decision-makers: Sven Eberth
---

# Flag a pending settlement on the payment entry, and mark the order paid only after settlement

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [MEM] Problem, the local flag ("Option 3") and the planned third state ("Option 1") — the memory does not record who decided.
> - [CODE] `UnzerOpenbankingPis.return_handler`, `mark_payments_pending`, the `TODO`.
> - [DERIVED] Option "mark paid on return" invented.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

With Unzer direct bank transfer (`UnzerOpenbankingPis`), the charge is `pending` and
nothing is charged yet when the customer returns from the bank; settlement takes one to
seven business days. `check_payment_state` requires the charged amount to equal the
total, so the return was treated as a failed payment and the customer saw an error for
an order that would be paid.

## Considered Options

* A provider-local override that flags the payment entry as `pending`
* A third payment state (`UNPAID` / `PENDING` / `PAID`) returned by
  `check_payment_state` for all providers, plus a hook for the pending case
* Mark the order as paid on return

## Decision Outcome

Chosen option: "provider-local flag", because it fixes the affected method without
changing the contract of `check_payment_state` for every provider.

`UnzerOpenbankingPis.return_handler` detects the pending charge and sets
`pending: True` on the order's payment entry (next to `charged` and `aborted`).
`is_paid` stays false; the settlement webhook (ADR-0015) sets it. A frontend reads the
flag to show "payment pending" instead of an error.

Marking the order paid on return would ship goods for money that may never arrive.

### Consequences

* Good, because the customer gets a correct confirmation and the order becomes paid only
  when the money arrived.
* Bad, because the flag is a convention of one provider. Other "pays later" methods have
  to set the same flag.
* Neutral: the third payment state remains the intended general solution. The override
  carries a `TODO` for it.

## More Information

* #198 (provider and pending flag), #216 (settlement webhook)
* `src/viur/shop/payment_providers/unzer_openbanking_pis.py`
