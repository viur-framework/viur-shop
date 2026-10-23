---
status: accepted
date: 2026-10-23
decision-makers: Sven Eberth
---

# Model the cart as a tree whose nodes decorate everything below them

## Context and Problem Statement

A cart is more than a flat list of articles. Articles get discounts; groups of articles
can go to different shipping addresses or come from different suppliers; a bundle sold
as one product consists of several articles; the whole cart has one billing context and
a default shipping address. And the same structure is needed for more than the active
basket — a wishlist stored in the customer account holds the same kind of content.

How should the cart be modeled so that all of this fits one data layout?

## Considered Options

* A tree (`Cart` is a ViUR `Tree`): nodes (`CartNodeSkel`) group and decorate, leaves
  (`CartItemSkel`) are articles
* A flat list of cart items with attributes for discount, address, group
* Separate models for basket, wishlist and groupings

## Decision Outcome

Chosen option: "a tree of decorating nodes", following the decorator pattern: a node
wraps what is below it and adds to it.

* **Leaves** are articles.
* **Nodes** group leaves and other nodes. A node can carry what applies to everything
  below it: a discount, a shipping address, a supplier, a name. Possible uses:
  * a discount on a node applies to its subtree — an article discount is applied by
    wrapping the qualifying article in its own node (`Cart.add_new_parent`);
  * individual shipping addresses per group;
  * grouping by supplier;
  * in theory, bundles: adding a bundle inserts a node with its articles below it, and
    the cart shows it as one bundle.
* **The root node is the cart.** What a sub-node does not set is taken from the closest
  node above it that does, up to the root — e.g. the shipping address
  (`Cart.get_closest_node`).
* **One layout for every kind of cart.** `cart_type` distinguishes the active basket
  (`BASKET`) from a wishlist (`WISHLIST`) kept in the customer account. The wishlist is
  rarely used so far, but it is the reason the cart is not tied to the checkout alone.

### Consequences

* Good, because new kinds of grouping or decoration are a new node, not a new model.
* Good, because totals, discounts and shipping are computed per node and add up the
  tree, the same way for every cart type.
* Bad, because every computation has to walk the tree, and readers must not assume a
  flat cart. A discount, an address or a shipping method may sit on any level.
* Bad, because the tree makes the cart harder to reason about and to send to systems that
  expect a flat list — the Unzer basket has to mirror the per-node computation
  (ADR-0008).
* Neutral: bundles and supplier grouping are possibilities of the model, not features
  that exist today.

## More Information

* `src/viur/shop/skeletons/cart.py` (`CartNodeSkel`, `CartItemSkel`),
  `src/viur/shop/modules/cart.py` (`add_new_parent`, `get_closest_node`,
  `get_available_root_nodes`), `src/viur/shop/types/enums.py` (`CartType`)
* The reasoning was stated by the maintainer when the decision records were written.
