---
status: accepted
date: 2026-10-07
decision-makers: Sven Eberth
---

# Let the Unzer keypair alone decide which customer types a payment method is offered to

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #214.
> - [SVEN] (session 677f6952) "nur am keypair orientieren"; chose "Alle Unzer-Provider"; "wir vertrauen darauf, dass wenn im keypair B2B steht, das auch technisch geht".
> - [DERIVED] "contract question, not a technical one"; the `cached_property` (Claude's implementation, not discussed).
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Unzer keypairs carry `allowCustomerTypes` (`"B2C"`, `"B2B"`, `"B2B,B2C"`) per payment
method. Measured in the sandbox, only the Pay later methods enforce it; SEPA direct
debit, EPS and prepayment accept a business customer on a B2C-only keypair. Unzer's
documentation states B2B support per method, but describes the method in general, not
what a merchant has booked.

## Considered Options

* Every Unzer provider checks the keypair's `allowCustomerTypes`
* Only the Pay later providers check it, since only those are enforced
* A `supported_customer_types` attribute per provider, taken from the documentation
* A configuration flag per provider in the project

## Decision Outcome

Chosen option: "every Unzer provider checks the keypair", because the keypair is what
the merchant booked with Unzer, and it is the only source that is specific to the
merchant. What the keypair allows is taken as working; what it does not allow is not
offered.

`UnzerAbstract.check_customer_type` is one of the usability checks (ADR-0012).

### Consequences

* Good, because the merchant's contract with Unzer, not shop code, decides the offer.
* Bad, because the shop is stricter than the API for methods that do not enforce the
  keypair. This is intended — accepting a customer type the merchant did not book is a
  contract question, not a technical one.
* Bad, because the keypair is read once per provider instance
  (`functools.cached_property`); a change at Unzer takes effect after an instance
  restart.

## More Information

* #214
* `src/viur/shop/payment_providers/unzer_abstract.py` (`check_customer_type`)
