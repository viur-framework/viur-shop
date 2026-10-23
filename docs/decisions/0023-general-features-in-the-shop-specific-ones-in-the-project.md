---
status: accepted
date: 2026-10-23
decision-makers: Sven Eberth
---

# General features belong in the shop, project-specific ones in the project

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [SVEN] (this conversation) A common base that can do as much as possible; individual cases in the project by overriding; not thousands of configuration options; skeletons are overridden in projects.
> - [SVEN] (this conversation, correction) Extensions of general interest do belong in the shop, enabled, disabled or parametrized by configuration; only what is foreseeably specific to one project stays out. Ideal: integrate the base class, configure it, have a working shop.
> - [CODE] `*_cls` parameters of `Shop`, hooks and events services.
> - [ASANA] (viur-shop board, task "Dashboard", open) "Erst als projektspezifische Komponente, später als Admin-Plugin" — used below as an example of the path from project to shop.
> - [DERIVED] The fork option and the "minimal shop" option; overridable methods as public API; the consequences. (The earlier rule "the shop provides the extension point, not the feature" was Claude's and is replaced by Sven's correction.)
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Every project that uses viur-shop has requirements of its own: other article models,
extra address fields, its own rules for shipping, discounts or payment availability,
its own frontend. It was clear from the start that the shop cannot cover all of them —
neither as built-in features nor through countless configuration options.

Which requirements belong in the shop, and how are the others met?

## Considered Options

* A complete, configurable base for what is of general interest; project-specific cases
  solved in the project by overriding and extending
* Cover every requirement in the shop and make it selectable through configuration
* A minimal shop that projects extend for everything beyond the core flow
* Let each project fork the shop

## Decision Outcome

Chosen option: "a complete, configurable base, with project-specific cases in the
project". The ideal is that a project integrates the shop with its base classes,
configures it, and has a working shop.

Where a requirement goes is decided by its reach:

* **Of general interest** — likely to be needed by more than one project: it belongs in
  the shop, and where it is not wanted everywhere it is enabled, disabled or parametrized
  through configuration of the shop.
* **Foreseeably specific to one project** — it stays in the project, built on the
  extension points below. Pulling every such detail into the shop would make the
  configuration grow without end.

A fork would lose every fix of the common base.

For the project-specific part, the shop is built to be extended:

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

For changes to the shop this means: ask whether a requirement is of general interest.
If it is, build it into the shop, configurable where needed. If it is not, it belongs in
the project — and if the project lacks a way to hook in, the shop adds the extension
point (an overridable method, a hook).

### Consequences

* Good, because a common requirement is built once and every project benefits from it
  and from its fixes.
* Good, because projects are not limited to what the shop's authors foresaw.
* Bad, because overridable methods and hooks become a public API: renaming them or
  changing their signature breaks projects, even when the shop itself does not call
  them differently.
* Bad, because each general feature adds configuration the shop has to keep working.
* Bad, because behavior depends on what a project overrides, which makes bug reports
  harder to reproduce with the shop alone.

## More Information

* `src/viur/shop/shop.py` (`Shop.__init__`), `src/viur/shop/services/hooks.py`,
  `src/viur/shop/services/events.py`
* Example of the path: an order dashboard is built as a project-specific component
  first, to become a shared admin plugin once it has proven itself.
* The reasoning was stated by Sven Eberth, creator and architect of viur-shop, when the decision records were written in October 2026.
