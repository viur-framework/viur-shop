---
status: accepted
date: 2026-10-23
decision-makers: Sven Eberth
---

# Scope viur-shop as a checkout; the article catalog stays in the project

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [SVEN] (this conversation) The shop is in practice a checkout; articles stay in the project; a standard article shop is too complex; rename to `viur-checkout` planned.
> - [ASANA] (viur-shop board, task "ViUR-Shop zu ViUR-Checkout umbenennen", created 2025-11-17 by a colleague, open) "Shop" means the whole (marketing, catalog, service, product selection, filtering and purchase); viur-shop should only provide the checkout; proposed names `ViUR-Checkout`, `-Backend`, `-UI`; open whether backend and frontend need distinct names.
> - [CODE] `Shop(article_skel=...)`, `ArticleAbstractSkel`.
> - [DERIVED] Options, consequences, "a rename needs its own record".
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

viur-shop was started to generalize the order process that every ViUR project used to
implement on its own: cart, order, discounts, shipping, payment. Over time it became
clear that the article side does not generalize: every project models its articles,
variants, prices and catalog pages differently, and a standard article shop would be
too complex to fit them.

What is viur-shop responsible for, and what stays in the project?

## Considered Options

* A checkout: the project defines the article, the shop handles cart, order and payment
* A complete shop including a standard article model and catalog

## Decision Outcome

Chosen option: "a checkout", because that is the part that is the same in every
project.

* The project passes its own article skeleton (`Shop(article_skel=...)`, derived from
  `ArticleAbstractSkel`). The shop reads what it needs for cart and order from it and
  does not manage the catalog.
* Frontends replace a large part of the default presentation, usually through
  [shop-components](https://github.com/viur-framework/shop-components).
* The name stays `viur-shop` for now. A rename to `viur-checkout`, which describes the
  scope better, is planned but not scheduled. "Shop" names the whole — marketing,
  catalog, service, product selection and filtering, and the purchase — while this
  package provides only the purchase. The proposal discussed so far: `viur-checkout`,
  with the backend and frontend packages named alike (e.g. `viur-checkout-backend`,
  `viur-checkout-ui`); not decided.

### Consequences

* Good, because projects keep full control over articles and catalog.
* Good, because the shop's scope stays small enough to be generic.
* Bad, because the name suggests more than the package does. New users expect a
  catalog.
* Neutral: a rename will be a breaking change for every project (package name, import
  path) and needs its own record.

## More Information

* `src/viur/shop/shop.py` (`Shop.__init__`, `article_skel`)
* The reasoning was stated by Sven Eberth, creator and architect of viur-shop, when the
  decision records were written in October 2026. The rename was first discussed in the
  team's task tracker in November 2025.
