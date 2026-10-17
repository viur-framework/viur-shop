import io
import itertools
import threading
import typing as t  # noqa

import cachetools

from viur import toolkit
from viur.core import current, db, errors
from viur.core.prototypes import List
from viur.core.skeleton import SkeletonInstance
from viur.shop import DEBUG_DISCOUNTS
from viur.shop.types import *
from .abstract import ShopModuleAbstract
from ..globals import MAX_FETCH_LIMIT, SHOP_LOGGER
from ..skeletons import CartItemSkel, CartNodeSkel, DiscountSkel
from ..types.dc_scope import DiscountValidator

logger = SHOP_LOGGER.getChild(__name__)

lock_current_automatically_discounts = threading.Lock()
"""Lock to make the current_automatically_discounts cache thread-safe"""


class Discount(ShopModuleAbstract, List):
    moduleName = "discount"
    kindName = "{{viur_shop_modulename}}_discount"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "percent"
        admin_info["editViews"] = [
            {
                "module": "shop/discount_condition",
                "title": "Conditions",
                "context": "condition.dest.key",
                "filter": {
                    # "is_subcode": True,
                    # "orderby": "scope_code",
                },
                # "columns": ["scope_code", "quantity_used"],
            }
        ]
        return admin_info

    # --- Apply logic ---------------------------------------------------------

    def search(
        self,
        code: str | None = None,
        discount_key: db.Key | None = None,
    ) -> list[SkeletonInstance]:
        if not isinstance(code, (str, type(None))):
            raise TypeError(f"code must be an instance of str")
        if not isinstance(discount_key, (db.Key, type(None))):
            raise TypeError(f"discount_key must be an instance of db.Key")
        if not bool(code) ^ bool(discount_key):
            raise ValueError(f"Need code xor discount_code")

        skel = self.viewSkel()
        if discount_key is not None:
            if not skel.read(discount_key):
                raise errors.NotFound
            return [skel]
        elif code is not None:
            # Get condition skel(s) with this code
            cond_skels = list(self.shop.discount_condition.get_by_code(code))
            logger.debug(f"{code = } yields <{len(cond_skels)}>{cond_skels = }")
            if not cond_skels:
                raise errors.NotFound
            # Get discount skel(s) using these condition skel
            discount_skels = (
                skel.all()
                .filter("condition.dest.__key__ IN", [s["key"] for s in cond_skels])
                .fetch(MAX_FETCH_LIMIT)
            )
            logger.debug(f"{code = } yields <{len(discount_skels)}>{discount_skels = }")
            return discount_skels
        else:
            raise InvalidStateError

    def apply(
        self,
        code: str | None = None,
        discount_key: db.Key | None = None,
    ) -> t.Any:
        if not isinstance(code, (str, type(None))):
            raise TypeError(f"code must be an instance of str")
        if not isinstance(discount_key, (db.Key, type(None))):
            raise TypeError(f"discount_key must be an instance of db.Key")
        if not bool(code is None) ^ bool(discount_key is None):
            raise MissingArgumentsException(f"{self}.apply", "code", "discount_code", one_of=True)
        if code is not None and not code:
            raise InvalidArgumentException("code", code)
        if discount_key is not None and not discount_key:
            raise InvalidArgumentException("discount_key", discount_key)
        cart_key = self.shop.cart.current_session_cart_key  # TODO: parameter?
        if cart_key is None:
            raise errors.PreconditionFailed("No basket created yet for this session")

        skels = self.search(code, discount_key)
        # logger.debug(f"{skels = }")

        if not skels:
            raise errors.NotFound
        for discount_skel in skels:
            # logger.debug(f'{discount_skel["name"]=} // {discount_skel["description"]=}')
            # logger.debug(f"{discount_skel = }")
            applicable, dv = self.can_apply(discount_skel, cart_key=cart_key, code=code)
            if applicable:
                break
        else:
            raise errors.NotFound("No valid code found")

        # logger.debug(f"Using {discount_skel=}")
        # logger.debug(f"Using {dv=}")

        try:
            application_domain = dv.application_domain
        except KeyError:
            raise InvalidStateError("application_domain not set")

        if discount_skel["discount_type"] == DiscountType.FREE_ARTICLE:
            cart_node_skel = self.shop.cart.cart_add(
                parent_cart_key=cart_key,
                name="Free Article",
                discount_key=discount_skel["key"],
            )
            # logger.debug(f"{cart_node_skel = }")
            cart_item_skel = self.shop.cart.add_or_update_article(
                article_key=discount_skel["free_article"]["dest"]["key"],
                parent_cart_key=cart_node_skel["key"],
                quantity=1,
                quantity_mode=QuantityMode.REPLACE,
            )
            # logger.debug(f"{cart_item_skel = }")
            return {  # TODO: what should be returned?
                "discount_skel": discount_skel,
                "cart_node_skel": cart_node_skel,
                "cart_item_skel": cart_item_skel,
            }
        elif application_domain == ApplicationDomain.BASKET:
            if discount_skel["discount_type"] in {DiscountType.PERCENTAGE, DiscountType.ABSOLUTE}:
                cart = self.shop.cart.cart_update(
                    cart_key=cart_key,
                    discount_key=discount_skel["key"]
                )
                # logger.debug(f"{cart = }")
                return {  # TODO: what should be returned?
                    "discount_skel": discount_skel,
                }
        elif application_domain == ApplicationDomain.ARTICLE:
            # In this case we check every article where this discount can be applied
            # and insert a new node with the discount.
            leafs_applied = []
            """Leafs to which the discount has been applied IN this request"""
            leafs_already = []
            """Leafs to which the discount has already applied BEFORE this request"""

            leaf_skels: list[SkeletonInstance_T[CartItemSkel]] = (
                self.shop.cart.viewSkel("leaf").all()
                .filter("parentrepo =", cart_key)
                .fetch(MAX_FETCH_LIMIT)
            )

            for leaf_skel in leaf_skels:
                # logger.debug(f"{leaf_skel=}")
                leaf_applicable, leaf_dv = self.can_apply(
                    discount_skel, cart_key=cart_key, article_skel=leaf_skel.article_skel, code=code
                )
                # logger.debug(f"{leaf_applicable=}, {leaf_dv=}")
                if leaf_applicable:
                    # Assign discount on new parent node for the leaf where the article is
                    parent_skel = self.shop.cart.viewSkel("node")
                    assert parent_skel.read(leaf_skel["parententry"])
                    if parent_skel["discount"] and parent_skel["discount"]["dest"]["key"] == discount_skel["key"]:
                        logger.info("Parent has already this discount key")
                        leafs_already.append(leaf_skel)
                        continue
                    parent_skel = self.shop.cart.add_new_parent(leaf_skel, name=f'Discount {discount_skel["name"]}')
                    cart = self.shop.cart.cart_update(
                        cart_key=parent_skel["key"],
                        discount_key=discount_skel["key"]
                    )
                    # logger.debug(f"{cart = }")
                    leafs_applied.append(leaf_skel)

            if not leafs_applied and not leafs_already:
                # applied to no article (neither now nor before)
                raise errors.NotFound("expected article is missing on cart")
            elif not leafs_applied and leafs_already:
                raise errors.NotFound("discount already applied to all applicable articles")
            return {  # TODO: what should be returned?
                "leaf_skel": leafs_applied,
                # "parent_skel": parent_skel,
                "discount_skel": discount_skel,
            }

        raise errors.NotImplemented(f'{discount_skel["discount_type"]=} is not implemented yet :(')

    def can_apply(
        self,
        skel: SkeletonInstance_T[DiscountSkel],
        *,
        cart_key: db.Key | None = None,
        article_skel: SkeletonInstance | None = None,
        code: str | None = None,
        context: DiscountValidationContext = DiscountValidationContext.NORMAL,
    ) -> tuple[bool, DiscountValidator | None]:
        logger.debug(f"--- Calling can_apply() ---")
        logger.debug(f'{skel["name"] = } // {skel["description"] = }')
        # logger.debug(f"{skel = }")

        if cart_key is None:
            cart = None
        else:
            cart = self.shop.cart.viewSkel("node")
            if not cart.read(cart_key):
                raise errors.NotFound

        if context == DiscountValidationContext.NORMAL and skel["activate_automatically"]:
            logger.info(f"looking for not automatically, but is automatically discount")
            return False, None

        dv = DiscountValidator()(
            cart_skel=cart, article_skel=article_skel,
            discount_skel=skel, code=code,
            context=context,
        )
        # logger.debug(f"{dv.is_fulfilled=} | {dv=}")

        if DEBUG_DISCOUNTS.get():
            # Use a buffer to make sure we write it on-block
            buffer = io.StringIO()
            print(f'Checking {skel["key"]!r} {skel["name"]}', file=buffer)
            for cv in dv.condition_validator_instances:
                code = f"{'+' if cv.is_fulfilled else '-'}"
                print(f'  {code} {dv.__class__.__name__} : '
                      f'{cv.condition_skel["key"]!r} {cv.condition_skel["name"]}', file=buffer)
                for s in cv.scope_instances:
                    code = f"{'+' if s.is_applicable else '-'}/{'+' if s.is_fulfilled else '-'}"
                    print(f"    {code} {s.__class__.__name__} : {s.is_applicable=} | {s.is_fulfilled=}", file=buffer)
            print(f">>> {dv.is_fulfilled=}", file=buffer)
            print(buffer.getvalue(), end="", flush=True)

        return dv.is_fulfilled, dv

    def revalidate_cart(
        self,
        cart_key: db.Key,
    ) -> list[SkeletonInstance_T[DiscountSkel]]:
        """
        Re-validate every discount applied to a cart and remove the invalid ones.

        A discount is validated once, when it is redeemed by :meth:`apply`.
        Afterwards the relation sits on the cart node and is folded into every
        price computation without being checked again, so a cart that outlives
        its discount's validity keeps the reduced total. This method checks the
        applied discounts against their scopes again -- using
        :attr:`DiscountValidationContext.REVALIDATE` -- and removes those which
        are no longer fulfilled.

        Frozen carts (belonging to a placed order) are skipped: their totals are
        snapshots and must not change anymore.

        In contrast to :meth:`remove`, which removes a discount from the whole
        cart on behalf of the customer, this removes exactly the nodes that have
        just been found invalid.

        :param cart_key: Key of the cart *root* node.
        :return: The discounts that have been removed, one entry per discount
            even if it was applied to several nodes.
        :raises TypeError: If ``cart_key`` is not a :class:`db.Key`.
        :raises errors.NotFound: If the cart node does not exist.
        """
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")

        cart_skel = self.shop.cart.viewSkel("node")
        if not cart_skel.read(cart_key):
            raise errors.NotFound
        if cart_skel["is_frozen"]:
            logger.debug(f"Skipping revalidation of the frozen cart {cart_key!r}")
            return []

        # Collect the nodes carrying a discount. The flat parentrepo index
        # covers the entire tree in one query, so there is no recursive walk
        # that could run into a cycle; the root node itself has no parentrepo
        # and is therefore added explicitly (as in
        # DiscountCondition.get_discounts_from_cart).
        nodes_by_discount: dict[db.Key, list[SkeletonInstance_T[CartNodeSkel]]] = {}
        seen_node_keys: set[db.Key] = set()
        node_skel: SkeletonInstance_T[CartNodeSkel]
        for node_skel in itertools.chain(
            (cart_skel,),
            toolkit.iter_skel(self.shop.cart.viewSkel("node").all().filter("parentrepo =", cart_key)),
        ):
            if node_skel["key"] in seen_node_keys or node_skel["is_frozen"] or not node_skel["discount"]:
                continue
            seen_node_keys.add(node_skel["key"])
            nodes_by_discount.setdefault(node_skel["discount"]["dest"]["key"], []).append(node_skel)

        # Validate everything before removing anything: dropping one discount
        # changes the cart's total and quantity, which feed the scopes of the
        # next one. Judging all of them by the same state keeps the outcome
        # independent of the iteration order.
        invalid_skels: list[SkeletonInstance_T[DiscountSkel]] = []
        for discount_key, discount_node_skels in nodes_by_discount.items():
            discount_skel = self.viewSkel()
            if not discount_skel.read(discount_key):
                # RelationalConsistency.SetNull should have cleared the relation;
                # a discount we cannot read is one we cannot judge either.
                logger.warning(f"Discount {discount_key!r} doesn't exist (anymore); cannot revalidate it")
                continue
            if self.is_still_applicable(discount_skel, cart_key=cart_key, node_skels=discount_node_skels):
                continue
            invalid_skels.append(discount_skel)

        for discount_skel in invalid_skels:
            for node_skel in nodes_by_discount[discount_skel["key"]]:
                logger.info(f'Removing no longer valid discount {discount_skel["key"]!r} '
                            f'({discount_skel["name"]!r}) from cart node {node_skel["key"]!r}')
                try:
                    if discount_skel["discount_type"] == DiscountType.FREE_ARTICLE:
                        # Drops the node together with the free article below it
                        self.shop.cart.cart_remove(cart_key=node_skel["key"])
                    else:
                        self.shop.cart.cart_update(cart_key=node_skel["key"], discount_key=None)
                except (errors.NotFound, errors.Forbidden, errors.Locked, AssertionError):
                    # A concurrent request may have changed the node meanwhile
                    logger.exception(f'Cannot remove discount {discount_skel["key"]!r} '
                                     f'from cart node {node_skel["key"]!r}')

        if invalid_skels:
            self.shop.cart.clear_caches()

        return invalid_skels

    def revalidate_session_basket(self) -> list[SkeletonInstance_T[DiscountSkel]]:
        """
        Re-validate the discounts of the current session basket, once per request.

        Called by the read endpoints that render the basket, so a discount that
        is no longer fulfilled already disappears from the cart the customer
        looks at, instead of falling away at the checkout only.

        :return: The discounts that have been removed.
        """
        request_data = current.request_data.get()
        if request_data.get("shop_basket_revalidated"):
            return []
        # Set before validating: removing a discount reads the cart again,
        # which must not trigger another revalidation.
        request_data["shop_basket_revalidated"] = True
        if (cart_key := self.shop.cart.current_session_cart_key) is None:
            return []
        return self.revalidate_cart(cart_key)

    def is_still_applicable(
        self,
        discount_skel: SkeletonInstance_T[DiscountSkel],
        *,
        cart_key: db.Key,
        node_skels: list[SkeletonInstance_T[CartNodeSkel]],
    ) -> bool:
        """
        Check whether an already applied discount is still fulfilled.

        The check mirrors the one :meth:`apply` performed when the discount was
        redeemed: same case distinction, same validation context object. A
        discount that was accepted back then must not be dropped now for a
        reason that never applied to it.

        :param discount_skel: The discount to check.
        :param cart_key: Key of the cart *root* node. The scopes resolve the
            cart's leafs via ``parentrepo``, which works for the root only.
        :param node_skels: The cart nodes this discount is applied to.
        :return: True if the discount may stay on the cart.
        """
        if discount_skel["discount_type"] == DiscountType.FREE_ARTICLE:
            # apply() validated this on cart level only; the free article itself
            # was never the target of the scopes.
            return self.can_apply(
                discount_skel, cart_key=cart_key,
                context=DiscountValidationContext.REVALIDATE,
            )[0]

        if any(
            condition["dest"]["application_domain"] == ApplicationDomain.BASKET
            for condition in discount_skel["condition"]
        ):
            # Same condition under which CartNodeSkel.total_discount_price
            # applies the reduction (see add_discount in skeletons/cart.py)
            return self.can_apply(
                discount_skel, cart_key=cart_key,
                context=DiscountValidationContext.REVALIDATE,
            )[0]

        # ApplicationDomain.ARTICLE: apply() checked every leaf on its own and
        # wrapped the qualifying ones into a node, so check those leafs again.
        checked_any = False
        for node_skel in node_skels:
            leaf_skel: SkeletonInstance_T[CartItemSkel]
            for leaf_skel in toolkit.iter_skel(
                self.shop.cart.viewSkel("leaf").all().filter("parententry =", node_skel["key"])
            ):
                checked_any = True
                if not self.can_apply(
                    discount_skel, cart_key=cart_key, article_skel=leaf_skel.article_skel,
                    context=DiscountValidationContext.REVALIDATE,
                )[0]:
                    return False
        # A wrapper node whose article has been removed from the cart meanwhile
        # has no leaf left, so there is nothing the discount could apply to.
        return checked_any

    @property
    @cachetools.cached(cache=cachetools.TTLCache(maxsize=1024, ttl=3600), lock=lock_current_automatically_discounts)
    def current_automatically_discounts(self) -> list[SkeletonInstance_T[DiscountSkel]]:
        query = self.viewSkel().all().filter("activate_automatically =", True)
        discounts = []
        for skel in query.fetch(MAX_FETCH_LIMIT):
            if not self.can_apply(skel, context=DiscountValidationContext.AUTOMATICALLY_PREVALIDATE)[0]:
                logger.debug(f'Skipping discount {skel["key"]} {skel["name"]} for current_automatically_discounts')
                continue
            discounts.append(skel)
        logger.debug(f'current_automatically_discounts {discounts=}')
        return discounts

    def remove(
        self,
        discount_key: db.Key,
    ) -> t.Any:
        if not isinstance(discount_key, db.Key):
            raise TypeError(f"discount_key must be an instance of db.Key")
        cart_key = self.shop.cart.current_session_cart_key  # TODO: parameter?

        discount_skel = self.viewSkel()

        if not discount_skel.read(discount_key):
            raise errors.NotFound
        try:
            # Todo what we do when we have more than more condition
            application_domain = discount_skel["condition"][0]["dest"]["application_domain"]
        except KeyError:
            raise InvalidStateError("application_domain not set")

        if discount_skel["discount_type"] == DiscountType.FREE_ARTICLE:
            for cart_skel in self.shop.cart.get_children(parent_cart_key=cart_key):
                if cart_skel["discount"] and cart_skel["discount"]["dest"]["key"] == discount_skel["key"]:
                    break
            else:
                raise errors.NotFound
            self.shop.cart.cart_remove(
                cart_key=cart_skel["key"]
            )

            return {  # TODO: what should be returned?
                "discount_skel": discount_skel}

        elif application_domain == ApplicationDomain.BASKET:
            self.shop.cart.cart_update(
                cart_key=cart_key,
                discount_key=None
            )
            return {  # TODO: what should be returned?
                "discount_skel": discount_skel,
            }

        elif application_domain == ApplicationDomain.ARTICLE:
            node_skels = (
                self.shop.cart.viewSkel("node").all()
                .filter("parentrepo =", cart_key)
                .filter("discount.dest.__key__ =", discount_key)
                .fetch(MAX_FETCH_LIMIT)
            )

            # logger.debug(f"<{len(node_skels)}>{node_skels=}")
            for node_skel in node_skels:
                # TODO: remove node, if no custom name, shipping, etc. is set? remove_parent flag?
                self.shop.cart.cart_update(
                    cart_key=node_skel["key"],
                    discount_key=None,
                )
            if not node_skels:
                raise errors.NotFound("Discount not used by any cart")
            return {  # TODO: what should be returned?
                "node_skels": node_skels,
                "discount_skel": discount_skel,
            }

        raise errors.NotImplemented(f'{discount_skel["discount_type"]=} is not implemented yet :(')
