---
status: accepted
date: 2026-09-15
decision-makers: Sven Eberth
---

# Cap "fetch all" queries at `MAX_FETCH_LIMIT`, and lift the cap only everywhere at once

## Context and Problem Statement

Many queries in viur-shop conceptually want *all* entries: the children of a cart node,
the active discounts, the conditions of a discount, the VAT rates, the addresses of a
user, the payments of an order. `Query.fetch()` needs an explicit limit, and an
unbounded loop over the datastore is a cost and latency risk on App Engine.

`MAX_FETCH_LIMIT = 100` in `globals.py` is used for these queries. To a reviewer it
looks like a silent truncation bug: a cart with 101 items would lose one.

## Considered Options

* One shared constant `MAX_FETCH_LIMIT = 100` for all "fetch all" queries
* Iterate without limit (`toolkit.iter_skel` / cursors) wherever "all" is meant
* Raise or remove the limit at the call site where truncation was noticed

## Decision Outcome

Chosen option: "one shared constant", because it bounds every query the same way and
keeps the computed values that depend on each other *consistently* incomplete instead
of inconsistent.

The last point is the important one. `CartNodeSkel` computes `total_discount_price`
from its children through the same `get_children` path that `build_node_items()` uses
for the Unzer basket. If only one of them is unbounded, the two disagree, and
`build_node_items()` derives a discount from the difference that does not exist — or
raises. Lifting the cap at a single call site turns a theoretical truncation into a real
inconsistency.

A shop that needs more entries raises the constant, which changes all call sites
together.

### Consequences

* Good, because every "fetch all" query is bounded and the bound is visible in one place.
* Good, because dependent computations stay consistent with each other.
* Bad, because more than 100 entries are silently truncated. In practice, cart nodes
  stay far below that.
* Neutral: `freeze_cart()` deliberately iterates without a limit, because a partially
  frozen cart would keep recomputing the unfrozen part after the order was placed.

### Confirmation

Before changing a limit at one call site, search for `MAX_FETCH_LIMIT` and for other
readers of the same entities. A reviewer rejects a change that lifts the limit on one
side of a computed pair only.

## More Information

* `src/viur/shop/globals.py` (`MAX_FETCH_LIMIT`)
* viur-core caps limits taken from request parameters at
  `conf.db.query_external_limit` (100) in `Query.mergeExternalFilter()`. A direct
  `fetch(limit)` call is not capped by the core. The shop constant mirrors that
  convention, it is not forced by it.
