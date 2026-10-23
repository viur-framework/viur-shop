---
status: accepted
date: 2026-10-07
decision-makers: Sven Eberth
---

# Separate a project's `is_available` from the provider's own usability checks

## Context and Problem Statement

Whether a payment provider is offered for an order had one switch: `is_available`, a
constructor argument the project sets (e.g. "only in this language"). Business customers
needed a second criterion the provider itself knows — whether its payment method accepts
that customer type — and the checkout needs a reason when a provider cannot be used,
not just a yes or no.

## Considered Options

* A list of checks on the provider, separate from the project's `is_available`
* Projects add the criterion to their own `is_available` callables
* A per-provider configuration flag
* `is_usable` returning a status object right away

## Decision Outcome

Chosen option: "a list of checks", because each criterion stays one method, subclasses
extend the list, and the same checks answer both "offer it?" and "why not?".

* `is_available` stays the project's condition, unchanged.
* `usability_checks()` returns the checks; each returns `ClientError | None`.
  `check_usable()` collects the errors, `is_usable()` is the yes/no form.
* A subclass adds a criterion with `[*super().usability_checks(), self.check_x]`.
* `get_payment_providers` / `payment_providers_list` and `can_checkout` use usability.
* The API exposes `is_usable: bool`. Reasons, if ever needed, come as an additional
  field, so the type of `is_usable` never changes.

### Consequences

* Good, because a new criterion is one method and does not touch projects.
* Bad, because it was breaking: the filter parameter `only_available` became
  `only_usable` without an alias, and `PaymentProviderResult.is_available` became
  `is_usable`. No known frontend used either.

## More Information

* #214
* `src/viur/shop/payment_providers/abstract.py` (`usability_checks`, `check_usable`,
  `is_usable`)
