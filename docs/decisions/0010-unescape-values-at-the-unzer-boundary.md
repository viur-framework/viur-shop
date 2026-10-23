---
status: accepted
date: 2026-10-02
decision-makers: Sven Eberth
---

# Unescape stored values where they leave for Unzer, not where they are stored

## Context and Problem Statement

viur-core's `StringBone` stores values HTML-escaped (`(` becomes `&#40;`, `'` becomes
`&#39;`). The shop passed address and customer values to Unzer unchanged, so escaped
strings showed up in Unzer's backend and on invoices. Every escaped character takes
five characters instead of one, which also pushed values over Unzer's length limits.

## Considered Options

* Unescape at the Unzer boundary (`as_plain_text()`)
* Store the address bones unescaped (`escape_html=False`)
* Both, plus a migration of the stored data

## Decision Outcome

Chosen option: "unescape at the Unzer boundary", because it fixes existing data at once
without touching storage, rendering or the escaping behavior of viur-core.

`as_plain_text()` is applied to every text value in `customer_from_order_skel()` and
`address_from_address_skel()`. Street name and number are joined first and unescaped
once, which also drops the trailing space when there is no house number.

`escape_html=False` changes what templates render and is a security trade-off for every
consumer of the bone. A migration needs a script writing to live data.

### Consequences

* Good, because Unzer receives what the customer typed.
* Bad, because every other external consumer (feeds, mails, exports) has to unescape on
  its own. The rule is general: **values leave the shop as plain text, unescaped at the
  boundary that sends them.**

## More Information

* #212
* `src/viur/shop/payment_providers/unzer_abstract.py` (`as_plain_text`)
