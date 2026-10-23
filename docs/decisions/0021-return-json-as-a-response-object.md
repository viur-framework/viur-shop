---
status: accepted
date: 2026-10-23
decision-makers: Sven Eberth
---

# Return JSON as a `JsonResponse` object instead of serializing in every endpoint

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [SVEN] (this conversation) Setting `Content-Type` in every response is cumbersome; a response class keeps the source data available in hooks; an experiment that stayed.
> - [CODE] `__str__` sets status and header; `ErrorResponse` overlaps.
> - [DERIVED] Sven named a decorator *or* a response class as ways to do it — listing the decorator as a rejected option is Claude's interpretation. Consequences are Claude's.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

In plain viur-core, an endpoint that returns JSON sets the `Content-Type` header on the
current response and returns the serialized string itself, in every method. Once the
string is built, the data behind it is gone: a hook or a wrapping method that gets the
return value only sees text.

## Considered Options

* A response class `JsonResponse` that carries the data and serializes itself
* Set the header and call `json.dumps` in every endpoint, as in viur-core
* A decorator that serializes the return value

## Decision Outcome

Chosen option: "a response class", because it removes the repeated header and
serialization code and keeps the source data available until the response is actually
written.

`JsonResponse(json_data, status_code=..., content_type=...)` stores the data. It sets the
status code and `Content-Type` and serializes with `ExtendedCustomJsonEncoder` only in
`__str__`, i.e. when ViUR renders the return value. Until then, code that holds the
response can read and change `json_data`.

This deviates from the viur-core convention on purpose. It was an experiment, and it
stayed.

### Consequences

* Good, because endpoints return data, not text, and the type annotation
  (`JsonResponse[dict[str, ...]]`) documents what they return.
* Good, because hooks and wrappers can work with the data.
* Bad, because it is a second way next to viur-core's, and contributors used to the core
  have to know it.
* Bad, because side effects happen in `__str__`: the status code and header are set at
  serialization time, not at construction.

## More Information

* `src/viur/shop/types/response.py`; used e.g. in `modules/api.py`, `modules/order.py`
* `types/error.py` has its own `ErrorResponse` that also serializes through
  `JsonResponse`. The error and response types overlap; unifying them is open.
* The reasoning was stated by Sven Eberth, the original author of viur-shop, when the decision records were written in October 2026.
