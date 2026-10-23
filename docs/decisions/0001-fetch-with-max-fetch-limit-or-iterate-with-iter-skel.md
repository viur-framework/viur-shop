---
status: accepted
date: 2026-09-15
decision-makers: Sven Eberth
---

# Fetch with `MAX_FETCH_LIMIT` where more than 100 entries are not expected, iterate with `iter_skel` where every entry is required

## Context and Problem Statement

Many queries in viur-shop conceptually want *all* entries: the children of a cart node,
the active discounts, the conditions of a discount, the VAT rates, the addresses of a
user, the payments of an order. `Query.fetch()` needs an explicit limit, and an
unbounded loop over the datastore is a cost and latency risk on App Engine.

`MAX_FETCH_LIMIT = 100` in `globals.py` is used for most of these queries. To a reviewer
it looks like a silent truncation bug: a cart with 101 items would lose one.

## Considered Options

* `fetch(MAX_FETCH_LIMIT)` everywhere
* `toolkit.iter_skel()` (iterates the query without a limit) everywhere
* Choose per query: `MAX_FETCH_LIMIT` where more than 100 entries are not expected,
  `iter_skel()` where every entry is required
* Raise or remove the limit at the call site where truncation was noticed

## Decision Outcome

Chosen option: "choose per query", because the two cases have different requirements.

**`fetch(MAX_FETCH_LIMIT)` is a compromise for queries whose result is expected to stay
far below 100** — more than 100 discounts on one cart, VAT rates or addresses of one user
are highly unlikely. 100 is viur-core's maximum for limits taken from a request
(`conf.db.query_external_limit` in its default configuration), so the shop uses the same
number. It bounds the query and keeps it a single `fetch()`.

**`toolkit.iter_skel()` is used where missing an entry would be a defect**, typically in
operations that change data or must be complete: freezing a cart (`freeze_cart`),
clearing or deleting its children (`cart_clear`, `_delete_children`), revalidating the
discounts of a cart tree (`revalidate_cart`, `is_still_applicable`), and tasks that walk
over entities. A partially frozen cart, for example, would keep recomputing — and
changing — the totals of its unfrozen entries after the order was placed.

The limit is never lifted at a single call site. `CartNodeSkel` computes
`total_discount_price` from its children through the same `get_children` path that
`build_node_items()` uses for the Unzer basket. Both are *consistently* incomplete
beyond 100 children. Lifting the limit on one side only makes them disagree, and
`build_node_items()` derives a discount from the difference that does not exist — or
raises. A shop that needs more entries raises the constant, which changes all call
sites together; a query that must be complete switches to `iter_skel()`.

### Consequences

* Good, because every bounded query is bounded the same way, visible in one place.
* Good, because operations that must be complete are complete.
* Good, because dependent computations stay consistent with each other.
* Bad, because beyond 100 entries a `MAX_FETCH_LIMIT` query truncates silently. That is
  the accepted trade-off for queries where this is not expected to happen.

### Confirmation

When adding a query, decide which case it is: "more than 100 is not expected" →
`fetch(MAX_FETCH_LIMIT)`; "every entry is required" → `iter_skel()`. Before changing a
limit at one call site, search for `MAX_FETCH_LIMIT` and for other readers of the same
entities.

## More Information

* `src/viur/shop/globals.py` (`MAX_FETCH_LIMIT`)
* `viur.toolkit.iter_skel()` iterates `query.iter()` and yields skeleton instances
  instead of calling `fetch()`.
* viur-core applies `conf.db.query_external_limit` (default 100) only in
  `Query.mergeExternalFilter()`, i.e. to limits from request parameters. A direct
  `fetch(limit)` is not capped by the core; the shop constant follows the convention,
  it is not forced by it.
