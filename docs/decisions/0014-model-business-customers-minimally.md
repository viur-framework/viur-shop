---
status: accepted
date: 2026-10-07
decision-makers: Sven Eberth
---

# Model business customers with the minimum Unzer needs

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #214.
> - [SVEN] (session 677f6952) "Registernummer + Defaults"; customer type not mixed with salutation; date of birth rules; "code-mäßig würde ich das auch nicht verbieten"; "viur-shop soll erstmal nur das benutzen was notwendig ist".
> - [DERIVED] Consequence about companies with another legal form.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

The address skeleton knew `customer_type`, but every customer reached Unzer as a
consumer. Unzer's business customer has a large optional model (company type, sector,
register type, owner) and some combinations are required by single payment methods
(e.g. `companyType` for the Pay later invoice authorize).

## Considered Options

* Derive the company information from one optional register number, with defaults
* Model sector, legal form and owner as bones
* Leave the company information to a project hook only
* Make the register number mandatory for business customers

## Decision Outcome

Chosen option: "derive from an optional register number", because the shop should only
use what is necessary. Filled register number: `registered`, `companyType=company`.
Empty: `not_registered`, `function=OWNER`, `commercialSector=OTHER`,
`companyType=other`. `company_info_from_order_skel()` can be overridden by a project.

A mandatory register number would exclude freelancers and sole traders, who have none.

Further rules:

* `customer_type` is its own field; it is not mixed into the salutation.
* A date of birth is required for consumers and unregistered businesses, not for
  registered ones.
* `vat_id` is stored with the address but not sent to Unzer, which has no field for it.
* The shop does not prevent a shipping recipient that differs from the business on the
  invoice, even though the Pay later invoice was refused for that in the sandbox. The
  customer sees the payment error.

### Consequences

* Good, because a business customer needs at most two extra fields.
* Bad, because companies with a register number but a different legal form are reported
  with the defaults unless the project overrides the hook.

## More Information

* #214, mausbrand/unzer-python-sdk#25, viur-framework/shop-components#71
* `src/viur/shop/payment_providers/unzer_abstract.py` (`company_info_from_order_skel`,
  `customer_from_order_skel`)
