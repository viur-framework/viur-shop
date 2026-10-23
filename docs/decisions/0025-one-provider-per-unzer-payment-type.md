---
status: accepted
date: 2024-01-25
decision-makers: Sven Eberth
---

# Implement one provider per Unzer payment type instead of using the Unzer Payment Page

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed · **[ASANA]** viur-shop task board.
>
> - [SVEN] (this conversation) The checkout this shop was first built for used the Unzer Payment Page. That project required the customer to choose the payment method explicitly before clicking "buy", so the Payment Page would only ever show one method — pointless. Hence every type is implemented individually. The Unzer integration and the Unzer SDK were first written inside that project; the SDK was published as a package because there was no Python SDK.
> - [CODE] One class per type in `payment_providers/unzer_*.py`; no Payment Page in `src/`; the frontend sends the created `typeId` to `save_type`.
> - [MEM] Types without payload fields in the SDK are created client-side (unzer-python-sdk `AGENTS.md`).
> - [HIST] (git history of the project the shop was extracted from, verified by Claude) 2021-06-15 `c71487630` "Implement unzer types as native types in OrderSkel and select them (exclude others)": the old flow opened the Payment Page with `excludeTypes` = every type except the chosen one. 2021-07-23 `5140f894a` "Implement bancontact directly (not supported by embedded payment page)". 2024-02-12 `d37c1f720` removed the in-repo SDK in favor of the PyPI package.
> - [DERIVED] Options, consequences.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Unzer offers two ways to take a payment: the hosted **Payment Page**, which lets the
customer pick among the enabled methods on Unzer's side, and the **UI components / payment
types**, where the shop creates or collects one specific payment type and authorizes or
charges it.

The first checkout this shop was built from used the Payment Page. Its requirements,
however, had the customer choose the payment method explicitly in the shop, before the
final "buy" click. So the Payment Page was opened with every other method excluded and
only ever showed that one method (2021). Some methods were not supported by the embedded
Payment Page at all and were already implemented directly then (Bancontact, 2021).

## Considered Options

* One payment provider per Unzer payment type
* The Payment Page, pre-filtered to the method chosen in the shop
* The Payment Page, with the method chosen on Unzer's side

## Decision Outcome

Chosen option: "one provider per payment type", because the method is chosen in the shop
anyway, and a hosted page that offers a single, already chosen method adds a redirect and
nothing else.

* Each method is its own provider class (`UnzerCard`, `UnzerPayPal`, `UnzerKlarna`,
  `UnzerPaylaterInvoice`, …), all derived from `UnzerAbstract`.
* Types the customer has to enter data for are created client-side with Unzer's UI
  components; the frontend sends the resulting `typeId` to `save_type`. Card data never
  reaches the shop.
* Each provider can carry its own rules: availability (ADR-0012, ADR-0013), field
  checks (ADR-0011), return handling (ADR-0016).

### Consequences

* Good, because the choice of method is part of the shop's checkout and can be validated
  before the order is placed.
* Good, because method-specific behavior lives in one class per method.
* Bad, because every new method needs its own provider and frontend integration; the
  Payment Page would bring new methods without code.
* Bad, because the shop follows Unzer's per-type APIs, which differ between methods
  (redirects, pending states, required customer data).

## More Information

* `src/viur/shop/payment_providers/unzer_abstract.py` (`save_type`),
  `src/viur/shop/payment_providers/unzer_*.py`
* The Unzer integration and the Unzer SDK (now
  [mausbrand/unzer-python-sdk](https://github.com/mausbrand/unzer-python-sdk)) were first
  written inside a project; the SDK was published because no Python SDK for Unzer
  existed.
* The reasoning was stated by Sven Eberth, creator and architect of viur-shop, when the
  decision records were written in October 2026.
