# AGENTS.md

Guidance for AI coding agents working in this repository. It covers what is specific to this
project — the general code style lives in `.editorconfig` and `tox.ini`.

## What this project is

`viur-shop` is a modular e-commerce extension for the [ViUR framework](https://www.viur.dev):
cart, order, discount, shipping, VAT and address modules, plus payment providers (Unzer,
PayPal, prepayment, invoice, Amazon Pay). Projects subclass and configure it; the companion
frontend is [shop-components](https://github.com/viur-framework/shop-components).

It runs inside projects that pin their own `viur-core`, on App Engine with several instances
and parallel requests. Many bugs here were races between requests or between instances —
keep that in mind for any state you introduce.

### What it is in practice: a checkout

The goal was to generalize the order process that every ViUR project used to build on its
own. In practice viur-shop is a **checkout**: it takes an article the project defines
(`article_skel`), puts it into a cart and handles ordering and payment. It does not own the
article catalog — that stays individual in each project (ADR-0020). A rename to
`viur-checkout` is planned for some point in the future; until then the name stays.

### A prototype, and it shows

viur-shop was the first ViUR plugin: a PyPI package a project imports and mounts as an
extension. It was also the first place several ideas were tried out, and some of them only
exist here so far:

- **Nested modules.** `Shop` is one module with the cart, order, discount, API and payment
  providers as sub-modules (`shop.cart`, `shop.api`, …). No other ViUR project uses that
  construct as extensively.
- **Deliberate deviations from viur-core conventions**, where the core way was found
  cumbersome. Example: endpoints return a `JsonResponse` object instead of setting the
  `Content-Type` header and serializing by hand in every method (ADR-0021).
- **Experiments that left traces.** Some things exist twice or look odd, e.g. the error and
  response types in `types/error.py` and `types/response.py`.

For changes this means: an oddity is not automatically a bug, and the viur-core way is not
automatically the target. Check the decision records. Do not unify duplicated mechanisms
along the way — that is a change of its own, to be agreed on first.

## Read the decision records first

Architectural decisions are recorded in [`docs/decisions/`](docs/decisions/README.md) as
MADR files. Several of them describe behavior that **looks like a bug and is deliberate** —
a fetch limit of 100, discounts sent to Unzer in a non-obvious shape, notes stored on the
cart instead of the session, return handlers without an ownership check.

- Before changing behavior in an area, check the index for a record on it. Read the record
  itself, not only its title.
- Only `accepted` records are binding. `proposed` ones describe intended direction,
  `superseded` ones are history.
- A change that contradicts an accepted record needs a new record that supersedes it, in the
  same pull request. Do not silently work around it, and do not edit the old record except
  for its `status`.
- A pull request that makes an architecturally significant decision adds a record from
  `docs/decisions/adr-template.md`. Write down only reasons that were actually stated or
  measured; if the reason is unknown, say so.
- A record states intent. Whether the code still does what the record says is decided by
  reading the code.

## Things that are easy to get wrong here

- **Placed orders are frozen.** Once `is_frozen` is set, computed bones must return the
  frozen value, and anything reproducing what the customer was charged reads
  `frozen_values`. A new computed bone has to respect this (ADR-0002).
- **No request state on bone instances.** Bones are shared by all skeletons of a class and
  all threads. Use `BaseBone.computing()`, the skeleton instance or `current.request_data`
  (ADR-0006).
- **Do not write the session unless something changed.** viur-core writes a changed session
  back as a whole and overwrites parallel requests (viur-framework/viur-core#1802, ADR-0004).
- **Caches are per process.** Clearing a cache reaches one App Engine instance; the TTL is the
  bound for all others (ADR-0005).
- **`MAX_FETCH_LIMIT` vs. `iter_skel`.** `fetch(MAX_FETCH_LIMIT)` is for queries where more
  than 100 entries are not expected; where every entry is required (freezing, deleting,
  tasks), iterate with `toolkit.iter_skel()`. Never lift the limit at a single call site
  (ADR-0001).
- **Values sent to external systems are unescaped at the boundary.** ViUR stores strings
  HTML-escaped (ADR-0010).
- **Unzer: the running sandbox API is the authority,** not Unzer's documentation and not the
  official SDKs. See `AGENTS.md` of
  [mausbrand/unzer-python-sdk](https://github.com/mausbrand/unzer-python-sdk) for measured
  examples. Payment state is always read from the API, never taken from a request or a
  webhook payload (ADR-0015, ADR-0018).

## Code style

- PEP 8, lines up to 120 characters, ignore list in `tox.ini`. CI runs `pycodestyle` on the
  diff against the base branch only:

  ```bash
  git diff -U0 origin/develop | pycodestyle --diff
  ```

- Spaces, LF, UTF-8, trailing newline — see `.editorconfig`.
- Double quotes, f-strings (also in `logging` calls).
- Type hints everywhere; built-in generics (`list[str]`) and `X | None`.
- Docstrings in Sphinx/reST format (`:param x:`, `:return:`).
- Multi-line dicts, lists and bone definitions end with a trailing comma.
- New code follows these rules even where the surrounding code does not.
- Do not remove commented-out code, `TODO`s or debug helpers you did not add yourself.

## Language

Code, comments, docstrings, commit messages and all repository files are written in English.
This is a public repository: it must contain no data, names or references from any customer
project — not in code, comments, commit messages, decision records or as "adapted from X"
attribution.

## Commits, branches and releases

- [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`,
  `refactor:`, `chore:`, …), code identifiers in backticks. Breaking changes as `feat!`/`fix!`
  with a `BREAKING CHANGE` footer.
- Branch off before committing: `fix/*` for patch-level, `feat/*` for minor-level work.
- Pull request target: fixes (patch level) against `main`, features (minor level) against
  `develop`. Raising a dependency floor is breaking and goes to `develop` (ADR-0007).
- Do not bump `src/viur/shop/version.py` in a feature or fix pull request. The version is set
  at release time in a separate `chore: bump version to vX.Y.Z` commit. Dependency pins belong
  in the pull request that needs them.
- Do not add `Co-Authored-By` trailers.

## Testing

There is no automated test suite in this repository yet. Verify a change against a ViUR
project running viur-shop, and state in the pull request what was verified and what was not.
Payment provider changes are verified against the provider's sandbox.
