---
status: accepted
date: 2026-10-20
decision-makers: Sven Eberth
---

# Cache discounts per process for 300 seconds, and clear the local cache on every edit

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #232.
> - [SVEN] (session 7d1a6b1f / 6ad34875) "sollten beim rabatt bearbeiten nicht dann die caches invalidiert werden?"; chose 300 s (Claude's recommendation) and the approved plan "TTL als Modul-Konstante".
> - [DERIVED] Rejection reasons for "configurable" and "shared version counter" are Claude's arguments from that session.
> - [MEM] Confirmation section (testing against the cache).
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

Every price build reads the automatic discounts, and every scope check reads its
discount condition. Both are cached per process (`cachetools.TTLCache`). With a TTL of
one hour and no invalidation, withdrawing a code, correcting a percentage or ending a
campaign early had no effect for up to an hour.

The caches live in the memory of each App Engine instance; an edit is handled by one
instance only.

## Considered Options

* Keep 3600 s, clear on edit
* Clear on edit and lower the TTL to 300 s, as a constant
* Make the TTL configurable
* A shared version counter in the datastore, checked on every request

## Decision Outcome

Chosen option: "clear on edit, 300 s as a constant (`DISCOUNT_CACHE_TTL`)", because
clearing only reaches the instance that handled the edit — the TTL is the upper bound
for every other instance, and an hour is too long for withdrawing a discount.

* Both caches are module-level objects so they can be cleared:
  `get_skel_cache`, `current_automatically_discounts_cache`.
* `Discount.clear_caches()` clears both under their locks, with `cache.clear()` — the
  decorator's `cache_clear()` is not guaranteed by the `cachetools>=5.0` pin.
* Called on add, edit, clone and delete of `Discount` and `DiscountCondition`.

A configurable TTL is more code without a known need. A shared version counter costs a
datastore read on every request.

### Consequences

* Good, because an edit takes effect immediately on the instance that handled it and
  within five minutes everywhere.
* Bad, because other instances serve the previous state for up to 300 s.
* Bad, because the caches are refilled twelve times as often. The extra reads were
  judged negligible, not measured.
* Neutral: date scopes are not affected by the TTL — the cached dates are compared with
  the current time on every check. Only an *edit* of the dates waits for the cache.

### Confirmation

When testing discount changes against a running server, expect the cache: a change made
directly in the datastore (not through the module) is not seen for up to 300 s.

## More Information

* #232
* `src/viur/shop/globals.py` (`DISCOUNT_CACHE_TTL`),
  `src/viur/shop/modules/discount.py`, `src/viur/shop/modules/discount_condition.py`
