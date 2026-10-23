---
status: accepted
date: 2026-10-23
decision-makers: Sven Eberth
---

# Provide a common base that projects extend by overriding, not a shop configured for every case

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [SVEN] (this conversation) A common base that can do as much as possible; individual cases in the project by overriding; not thousands of configuration options; skeletons are overridden in projects.
> - [CODE] `*_cls` parameters of `Shop`, hooks and events services.
> - [DERIVED] The fork option; the rule "the shop provides the extension point, not the feature"; overridable methods as public API; the consequences.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Every project that uses viur-shop has requirements of its own: other article models,
extra address fields, its own rules for shipping, discounts or payment availability,
its own frontend. It was clear from the start that the shop cannot cover all of them —
neither as built-in features nor as configuration options.

How does the shop deal with requirements it does not cover?

## Considered Options

* A common base that does as much as possible, with individual cases solved in the
  project by overriding and extending
* Cover the requirements in the shop and make them selectable through configuration
* Let each project fork the shop

## Decision Outcome

Chosen option: "a common base, extended in the project", because a configuration option
for every project requirement would grow without end, and a fork would lose every fix
of the common base.

The shop is built for this:

* **Module classes** are constructor parameters of `Shop` (`address_cls`, `cart_cls`,
  `order_cls`, `discount_cls`, …), so a project subclasses a module and passes its own.
* **Skeletons** can be extended in the project, e.g. with additional bones. The feature
  set of the shop is the starting point, not the limit — supplier grouping or bundles
  (ADR-0022) are examples a project can build on the cart tree.
* **Hooks and events** (`services/hooks.py`, `services/events.py`) let a project replace
  single steps (`Customization` per `Hook`) or react to events without subclassing.
* **Payment providers** are classes a project instantiates, subclasses or adds, and
  their availability is a project callable (`is_available`, ADR-0012).
* The frontend is replaced largely anyway, usually through shop-components.

For changes to the shop this means: a project-specific requirement belongs in the
project. The shop provides the extension point if one is missing — a method that can be
overridden, a hook — rather than the feature or a configuration flag for it.

### Consequences

* Good, because the common base stays generic and every project benefits from its fixes.
* Good, because projects are not limited to what the shop's authors foresaw.
* Bad, because overridable methods and hooks become a public API: renaming them or
  changing their signature breaks projects, even when the shop itself does not call
  them differently.
* Bad, because behavior depends on what a project overrides, which makes bug reports
  harder to reproduce with the shop alone.

## More Information

* `src/viur/shop/shop.py` (`Shop.__init__`), `src/viur/shop/services/hooks.py`,
  `src/viur/shop/services/events.py`
* The reasoning was stated by the maintainer when the decision records were written.
