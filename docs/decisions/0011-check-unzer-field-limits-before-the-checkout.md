---
status: accepted
date: 2026-10-02
decision-makers: Sven Eberth
---

# Check Unzer's field limits in `can_checkout`, with the limits owned by the SDK

## Context and Problem Statement

Unzer refuses a payment mid-checkout when one field is a character too long, and the
customer only sees that the checkout failed. By then the order may already be frozen.
The limits documented in the SDK docstrings were wrong (measured: `street` 64, not 50;
`firstname`/`lastname` 40 each on the customer).

## Considered Options

* Limits in the SDK only (validated before the request)
* Limits in the SDK, and viur-shop reports them in `can_checkout`
* Truncate over-long values
* Limits as constants in viur-shop

## Decision Outcome

Chosen option: "limits in the SDK, reported by `can_checkout`", because the limits are a
property of the API and belong to the client that talks to it, while only the shop can
turn a violation into an error the customer can fix while the cart is still editable.

`can_checkout` builds the Unzer customer and calls `validateBeforeRequest()`; a
`ValueError` becomes a `ClientError`. Values are not truncated — a truncated name would
reach invoices and the payment partner.

### Consequences

* Good, because the customer learns about an over-long field before the order is frozen
  and can correct it.
* Bad, because a customer with a name longer than the limit cannot pay with Unzer.
  Sending a truncated customer name together with the full billing name would work
  (measured), but was deliberately not built.
* Neutral: the check only takes effect with an SDK release that ships the limits; the
  `unzer` pin has to include it.

## More Information

* #213, mausbrand/unzer-python-sdk#24
* `src/viur/shop/payment_providers/unzer_abstract.py` (`can_checkout`)
