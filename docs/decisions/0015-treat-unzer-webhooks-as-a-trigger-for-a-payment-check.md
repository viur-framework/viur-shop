---
status: accepted
date: 2026-10-16
decision-makers: Sven Eberth
---

# Treat Unzer webhooks as a trigger for a payment check, never as the payment state

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #216, #231.
> - [SVEN] (session e863ddcb) "ja, mach den PR mit 200 OK"; on `charge.failed`: "ist das wichtig für uns?" → left unhandled.
> - [DERIVED] Framing "never as the payment state"; option 2 (apply payload state) invented; one webhook URL for all providers was Claude's answer, not Sven's decision.
> - [CODE] `UnzerAbstract.webhook` only schedules `check_payment_deferred`.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Unzer notifies the shop about payment events by webhook. A notification can arrive
before or after the customer returns through the return handler, can arrive several
times, and some payment methods settle days after the payment is completed. Direct bank
transfer completes the payment while the charge is still pending and signals the
settlement only with `charge.succeeded`.

## Considered Options

* The webhook only schedules a payment check that reads the state from the Unzer API
* The webhook applies the state from its payload

## Decision Outcome

Chosen option: "only schedule a check", because the API is the authority and the check
is idempotent — a repeated or out-of-order notification ends in "already marked as
paid".

* `payment.completed` and `charge.succeeded` schedule `check_payment_deferred` with a
  delay, so the check does not collide with the return handler.
* Other events are acknowledged and ignored. `charge.failed` is not handled: such an
  order stays unpaid.
* The webhook answers `200 OK`. Unzer documents that as the acknowledgement; with `204`
  every notification was redelivered for about twelve hours on a production shop.
* One webhook URL serves all Unzer providers, because the order lookup by payment id and
  the check live in `UnzerAbstract`.

### Consequences

* Good, because duplicates, retries and ordering do not matter.
* Good, because a payload that differs from the API state cannot mark an order as paid.
* Bad, because every notification costs an API call.
* Bad, because merchants have to subscribe to the `charge` events for deferred
  settlements.
* Neutral: whether `200 OK` stops the redeliveries has not been verified after a
  release. A `charge.succeeded` payload has not been observed yet; it is assumed to
  carry `paymentId`.

## More Information

* #216 (`charge.succeeded`), #231 (`200 OK`)
* `src/viur/shop/payment_providers/unzer_abstract.py` (`webhook`)
* `PaypalCheckout.webhook` still answers `204`; nothing was measured for PayPal.
