---
status: accepted
date: 2026-10-07
decision-makers: Sven Eberth
---

# Let the Unzer keypair alone decide which customer types a payment method is offered to

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
