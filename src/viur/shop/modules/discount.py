import functools
import typing as t  # noqa

from viur.core import db, errors
from viur.core.prototypes import List
from viur.core.skeleton import SkeletonInstance
from viur.shop.types import *
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER
from ..types.dc_scope import DiscountValidator

logger = SHOP_LOGGER.getChild(__name__)


class Discount(ShopModuleAbstract, List):
    kindName = "shop_discount"

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
            if not skel.fromDB(discount_key):
                raise errors.NotFound
            return [skel]
        elif code is not None:
            # Get condition skel(s) with this code
            cond_skels = list(self.shop.discount_condition.get_by_code(code))
            logger.debug(f"{code = } yields <{len(cond_skels)}>{cond_skels = }")
            if not cond_skels:
                raise errors.NotFound
            # Get discount skel(s) using these condition skel
            discount_skels = skel.all().filter("condition.dest.__key__ IN", [s["key"] for s in cond_skels]).fetch(100)
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
        if not bool(code) ^ bool(discount_key):
            raise ValueError(f"Need code xor discount_code")
        cart_key = self.shop.cart.current_session_cart_key  # TODO: parameter?

        skels = self.search(code, discount_key)
        # logger.debug(f"{skels = }")

        if not skels:
            raise errors.NotFound
        for discount_skel in skels:
            logger.debug(f'{discount_skel["name"]=} // {discount_skel["description"]=}')
            # logger.debug(f"{discount_skel = }")
            applicable, dv = self.can_apply(discount_skel, cart_key, code)
            if applicable:
                logger.debug("is applicable")
                break
            else:
                logger.error(f"{dv = }")
        else:
            raise errors.NotFound("No valid code found")

        logger.debug(f"Using {discount_skel=}")
        logger.debug(f"Using {dv=}")

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
            logger.debug(f"{cart_node_skel = }")
            cart_item_skel = self.shop.cart.add_or_update_article(
                article_key=discount_skel["free_article"]["dest"]["key"],
                parent_cart_key=cart_node_skel["key"],
                quantity=1,
                quantity_mode=QuantityMode.REPLACE,
            )
            logger.debug(f"{cart_item_skel = }")
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
                logger.debug(f"{cart = }")
                return {  # TODO: what should be returned?
                    "discount_skel": discount_skel,
                }
        elif application_domain == ApplicationDomain.ARTICLE:
            all_leafs = []
            for cv in dv.condition_validator_instances:
                if cv.is_fulfilled and cv.condition_skel["scope_article"] is not None:
                    leaf_skels = (
                        self.shop.cart.viewSkel("leaf").all()
                        .filter("parentrepo =", cart_key)
                        .filter("article.dest.__key__ =", cv.condition_skel["scope_article"]["dest"]["key"])
                        .fetch()
                    )
                    logger.debug(f"<{len(leaf_skels)}>{leaf_skels = }")
                    # if not leaf_skels:
                    #     raise errors.NotFound("expected article is missing on cart")
                    # if len(leaf_skels) > 1:
                    #     raise NotImplementedError("article is ambiguous")
                    for leaf_skel in leaf_skels:
                        # Assign discount on new parent node for the leaf where the article is
                        parent_skel = self.shop.cart.viewSkel("node")
                        assert parent_skel.fromDB(leaf_skel["parententry"])
                        if parent_skel["discount"] and parent_skel["discount"]["dest"]["key"] == discount_skel["key"]:
                            logger.info("Parent has already this discount key")
                            continue
                        parent_skel = self.shop.cart.add_new_parent(leaf_skel, name=f'Discount {discount_skel["name"]}')
                        cart = self.shop.cart.cart_update(
                            cart_key=parent_skel["key"],
                            discount_key=discount_skel["key"]
                        )
                        logger.debug(f"{cart = }")
                        all_leafs.append(leaf_skels)
            if not all_leafs:
                raise errors.NotFound("expected article is missing on cart (or discount exist already)")
            return {  # TODO: what should be returned?
                "leaf_skel": all_leafs,
                # "parent_skel": parent_skel,
                "discount_skel": discount_skel,
            }
        raise errors.NotImplemented(f'{discount_skel["discount_type"]=} is not implemented yet :(')

    def can_apply(
        self,
        skel: SkeletonInstance,
        cart_key: db.Key | None = None,
        code: str | None = None,
        as_automatically: bool = False,
    ) -> tuple[bool, DiscountValidator | None]:
        logger.debug(f'{skel["name"] = } // {skel["description"] = }')
        # logger.debug(f"{skel = }")

        if cart_key is None:
            cart = None
        else:
            cart = self.shop.cart.viewSkel("node")
            if not cart.fromDB(cart_key):
                raise errors.NotFound

        if not as_automatically and skel["activate_automatically"]:
            logger.info(f"is activate_automatically")
            return False, None

        dv = DiscountValidator()(cart_skel=cart, discount_skel=skel, code=code)
        return dv.is_fulfilled, dv

    @property
    @functools.cache
    def current_automatically_discounts(self) -> list[SkeletonInstance]:
        query = self.viewSkel().all().filter("activate_automatically =", True)
        discounts = []
        for skel in query.fetch(100):
            if not self.can_apply(skel, as_automatically=True)[0]:
                # TODO: this can_apply must be limited (check only active state, time range, ... but not lang)
                logger.debug(f'Skipping discount {skel["key"]} {skel["name"]}')
                continue
            discounts.append(skel)
        logger.debug(f'current {discounts=}')
        return discounts
