# Architecture Decision Records

Decisions that shape viur-shop and would be easy to undo by accident — things that look
like gaps or bugs but are deliberate. Format and conventions: [ADR-0000](0000-use-markdown-architectural-decision-records.md).
New records start from [adr-template.md](adr-template.md).

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft — remove before merge.** Every record and `AGENTS.md` carry a provenance callout below
> their title, marking what Claude took from Sven, from PR descriptions, from its memory notes,
> from the code, from the team's task tracker (`[ASANA]`), from the git history of the project the shop was extracted from (`[HIST]`), and what it derived itself. To strip them, delete everything between the
> `DRAFT-PROVENANCE:START` and `DRAFT-PROVENANCE:END` comments.
<!-- DRAFT-PROVENANCE:END -->

| ADR | Decision | Status |
|---|---|---|
| [0000](0000-use-markdown-architectural-decision-records.md) | Record architectural decisions as Markdown ADRs (MADR) | proposed |
| [0001](0001-fetch-with-max-fetch-limit-or-iterate-with-iter-skel.md) | Fetch with `MAX_FETCH_LIMIT` where more than 100 entries are not expected, iterate with `iter_skel` where every entry is required | accepted |
| [0002](0002-freeze-the-cart-as-the-record-of-the-order.md) | Freeze the cart when the order is placed; frozen values are the record of the order | accepted |
| [0003](0003-revalidate-applied-discounts-before-the-checkout.md) | Revalidate applied discounts in their own context, drop invalid ones and refuse that checkout attempt | accepted |
| [0004](0004-store-customer-notes-on-the-cart.md) | Store notes to the customer on the cart, not in the session | accepted |
| [0005](0005-cache-discounts-per-process-with-a-short-ttl.md) | Cache discounts per process for 300 seconds, and clear the local cache on every edit | accepted |
| [0006](0006-keep-request-state-off-bone-instances.md) | Keep request state off bone instances; guard computations per skeleton and thread | accepted |
| [0007](0007-pin-viur-core-by-exclusion-and-raise-floors-in-minor-releases.md) | Exclude broken viur-core releases individually; raising a dependency floor is a breaking change | accepted |
| [0008](0008-send-basket-discounts-to-unzer-as-positive-item-discounts.md) | Send basket discounts to Unzer as positive per-item discounts, split in whole cents | accepted |
| [0009](0009-prefix-every-id-sent-to-unzer.md) | Prefix every id sent to Unzer with `s` or `p` | accepted |
| [0010](0010-unescape-values-at-the-unzer-boundary.md) | Unescape stored values where they leave for Unzer, not where they are stored | accepted |
| [0011](0011-check-unzer-field-limits-before-the-checkout.md) | Check Unzer's field limits in `can_checkout`, with the limits owned by the SDK | accepted |
| [0012](0012-separate-project-availability-from-provider-usability.md) | Separate a project's `is_available` from the provider's own usability checks | accepted |
| [0013](0013-let-the-unzer-keypair-decide-customer-types.md) | Let the Unzer keypair alone decide which customer types a payment method is offered to | accepted |
| [0014](0014-model-business-customers-minimally.md) | Model business customers with the minimum Unzer needs | accepted |
| [0015](0015-treat-unzer-webhooks-as-a-trigger-for-a-payment-check.md) | Treat Unzer webhooks as a trigger for a payment check, never as the payment state | accepted |
| [0016](0016-flag-a-pending-settlement-without-marking-the-order-paid.md) | Flag a pending settlement on the payment entry, and mark the order paid only after settlement | accepted |
| [0017](0017-enforce-cart-ownership-in-the-exposed-api-endpoints.md) | Enforce cart ownership in the exposed API endpoints, with the rule in the cart module | proposed |
| [0018](0018-no-ownership-check-in-payment-return-handlers.md) | Do not check session ownership in the payment return handlers | accepted |
| [0019](0019-consume-individual-discount-codes-when-the-order-is-placed.md) | Mark an individual discount code as used when the order is placed | proposed |
| [0020](0020-scope-viur-shop-as-a-checkout.md) | Scope viur-shop as a checkout; the article catalog stays in the project | accepted |
| [0021](0021-return-json-as-a-response-object.md) | Return JSON as a `JsonResponse` object instead of serializing in every endpoint | accepted |
| [0022](0022-model-the-cart-as-a-tree-of-decorating-nodes.md) | Model the cart as a tree whose nodes decorate everything below them | accepted |
| [0023](0023-general-features-in-the-shop-specific-ones-in-the-project.md) | General features belong in the shop, project-specific ones in the project | accepted |
| [0024](0024-compute-prices-as-floats-rounded-to-cents.md) | Compute prices as floats rounded to cents, until a switch to `Decimal` is decided | accepted |
| [0025](0025-one-provider-per-unzer-payment-type.md) | Implement one provider per Unzer payment type instead of using the Unzer Payment Page | accepted |
| [0026](0026-separate-the-discount-value-from-its-conditions.md) | Separate the discount value from its conditions, and combine conditions with `ONE_OF` or `ALL` | accepted |
