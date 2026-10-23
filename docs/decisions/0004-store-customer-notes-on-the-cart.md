---
status: accepted
date: 2026-10-20
decision-makers: Sven Eberth
---

# Store notes to the customer on the cart, not in the session

<!-- DRAFT-PROVENANCE:START -->
> [!WARNING]
> **Draft provenance — remove before merge.** Written by Claude, not yet reviewed.
> Tags: **[SVEN]** stated or confirmed by Sven · **[PR]** taken from a PR description ·
> **[MEM]** Claude's memory notes from earlier sessions · **[CODE]** checked by Claude in the code ·
> **[DERIVED]** Claude's own inference or wording, unconfirmed.
> Quotes come from session transcripts (session id in brackets), typos corrected.
>
> - [PR] #236 ("Why on the cart and not in the session"), #238.
> - [SVEN] (session 6ad34875) "ich rechne nicht mit einer zeitnahen core lösung"; "wie wäre es mit einem messages feld (multiple stringbone oder recordbone)"; dismissal: "Kunde schließt"; field renames (`key` identifies, no `id`).
> - [CODE] Docstring of `CartNodeSkel.messages`.
> - [DERIVED] "a note costs a cart write"; folding #238 in as a general rule.
> - [ASANA] (kickoff board "Shop", requirements collected 2023-10-18 from three projects before any code was written; a first draft, partly outdated) Task "Konsequentes Error-Handling für Kunden-Transparenz": pass errors from the payment provider through to the customer, "Artikel, Rabatt gibt es nicht mehr etc.", translated in a customer-friendly way.
<!-- DRAFT-PROVENANCE:END -->

## Context and Problem Statement

The shop sometimes changes a cart on its own — since ADR-0003 it drops a discount that
no longer applies. The customer must be told, but the basket endpoints have no error
channel, and the request that makes the change is often not the one the customer looks
at: a mini cart on any page usually reads the basket first.

## Considered Options

* A one-time queue in the ViUR session (flash messages)
* A response header or a redirect parameter
* A dedicated datastore kind per note
* A specific relation on the cart (e.g. `removed_discount`)
* A generic `messages` field on the cart node

## Decision Outcome

Chosen option: "generic `messages` field on the cart node", because it is the only
option that survives parallel requests and does not depend on which request made the
change.

The session queue was implemented first and failed, measured: `Session.save()` writes
the session back as a whole for every request that marked it changed, so parallel
requests of one page load restored an entry that was just picked up, or lost a new one
(viur-framework/viur-core#1802). Making only the shop's write transactional does not
help, because the other request still overwrites blindly. A fix in viur-core was not
expected soon.

The schema:

* `CartNodeSkel.messages` is a `RecordBone` of `CartMessageSkel`, `readOnly`,
  not indexed.
* `key` identifies an entry (UUID4, computed once). `translation_key` is the text and
  the stable type of the note, `translation_variables` the values for its
  placeholders — so the frontend renders it in the language the cart is viewed in.
  Data a frontend needs beyond the text goes into a separate bone later, never into
  `translation_variables`.
* `Cart.add_message()` / `remove_message()` write in a transaction
  (`Skeleton.patch`). An identical entry is not added twice. Frozen carts are left alone.
* A note stays until the customer dismisses it (`api/message_remove`, ownership checked).
  Neither rendering nor a later cart change counts as "seen".

### Consequences

* Good, because parallel revalidations write the same entry; there is nothing to pick
  up and nothing to race.
* Good, because new kinds of notes (e.g. a reset shipping method, #239) reuse the field
  and the endpoint.
* Bad, because a note costs a cart write.

### Related rule: write the session only when it changed

The same viur-core behavior makes every unconditional `markChanged()` a potential
overwrite of parallel requests. Shop code marks the session as changed only when a
value actually changed (#238).

## More Information

* Origin: the requirements collected before the first line of code (October 2023) asked
  for consistent error handling towards the customer — errors passed through from the
  payment provider, and notices such as "this article or discount no longer exists",
  translated for the customer.
* #236 (messages), #238 (session writes), viur-framework/viur-core#1802
* `src/viur/shop/skeletons/cart.py` (`CartMessageSkel`, `CartNodeSkel.messages`)
* Rejected alternatives: header or redirect — lost when another request made the change;
  dedicated kind — works, but the most effort; `removed_discount` relation — not
  generic.
