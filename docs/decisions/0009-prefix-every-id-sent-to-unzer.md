---
status: accepted
date: 2026-09-11
decision-makers: Sven Eberth
---

# Prefix every id sent to Unzer with `s` or `p`

## Context and Problem Statement

Unzer refuses a whole request with `400 API.500.560.003` ("sensitive card information
in BODY") when any string value looks like a card number. ViUR ids are 16 digits; some
fall into a card BIN range and are Luhn-valid by chance. Such an order could never be
paid, every retry failed the same way, and the message pointed at card data where none
was involved.

Measured against the sandbox: the check reads each value as a whole, strips separators,
and needs both a card BIN range and a valid Luhn checksum. A single letter in front is
enough to pass.

## Considered Options

* Prefix all ids with `s` (sandbox) or `p` (production)
* Send the urlsafe key instead of the numeric id
* Prefix only the fields that were seen failing

## Decision Outcome

Chosen option: "prefix all ids", because the customer id already carried this prefix to
keep the sandbox and production customer bases apart — it becomes one convention for
`customerId`, `orderId` and `basketItemReferenceId`, in `external_id()`. No hyphen, so
the ids stay distinguishable from Unzer's own `s-pay-…` scheme.

Reading ids back (`get_order_by_pay_id()`, the webhook path) tries the raw value first
and the stripped value second. Stripping blindly would resolve a legacy key *named*
`s123` to the unrelated order `123`.

### Consequences

* Good, because no order can be blocked by its own key.
* Good, because sandbox and production data cannot be mixed up by id.
* Bad, because every reader of an Unzer id has to go through `parse_external_id()` /
  `external_id_candidates()`; a direct key lookup misses prefixed ids.

## More Information

* #210
* `src/viur/shop/payment_providers/unzer_abstract.py` (`external_id`,
  `external_id_candidates`)
