import logging

from viur.core import current, db, errors, utils
from viur.core.prototypes import List
from viur.core.skeleton import skeletonByKind
from .abstract import ShopModuleAbstract
from .. import CodeType, DiscountType, QuantityMode
from ..exceptions import InvalidStateError

logger = logging.getLogger("viur.shop").getChild(__name__)


class Discount(ShopModuleAbstract, List):
    kindName = "shop_discount"

    def search(
        self,
        code: str | None = None,
        discount_key: db.Key | None = None,
    ) -> None:
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
        elif code is not None:
            skel = skel.all().filter("condition.dest.scope_code =", code).getSkel()
            if skel is None:
                raise errors.NotFound
        else:
            raise InvalidStateError

        logger.debug(f"{skel = }")

        return skel

    def apply(
        self,
        code: str | None = None,
        discount_key: db.Key | None = None,
    ) -> None:
        if not isinstance(code, (str, type(None))):
            raise TypeError(f"code must be an instance of str")
        if not isinstance(discount_key, (db.Key, type(None))):
            raise TypeError(f"discount_key must be an instance of db.Key")
        if not bool(code) ^ bool(discount_key):
            raise ValueError(f"Need code xor discount_code")
        cart_key = self.shop.cart.current_session_cart_key  # TODO: parameter?

        skel = self.search(code, discount_key)
        logger.debug(f"{skel = }")

        if skel is None:
            raise errors.NotFound
        if not self.can_apply(skel, cart_key):
            return False

        if skel["discount_type"] == DiscountType.FREE_ARTICLE:
            cart_node_skel = self.shop.cart.cart_add(
                parent_cart_key=cart_key,
                name="Free Article",
                discount_key=skel["key"],
            )
            logger.debug(f"{cart_node_skel = }")
            cart_item_skel = self.shop.cart.add_or_update_article(
                article_key=skel["free_article"]["dest"]["key"],
                parent_cart_key=cart_node_skel["key"],
                quantity=1,
                quantity_mode=QuantityMode.REPLACE,
            )
            logger.debug(f"{cart_item_skel = }")
            return {
                "discount_skel": skel,
                "cart_node_skel": cart_node_skel,
                "cart_item_skel": cart_item_skel,
            }

        return skel

    def can_apply(
        self,
        skel,
        cart_key: db.Key | None = None,
        code: str | None = None,
    ):
        logger.debug(f"{skel = }")

        cart = self.shop.cart.viewSkel("node")
        if not cart.fromDB(cart_key):
            raise errors.NotFound

        # We need the full skel with all bones (otherwise the refSkel would be to large)
        condition_skel = skeletonByKind(skel.condition.kind)()
        for condition in skel["condition"]:
            if not condition_skel.fromDB(condition["dest"]["key"]):
                logger.warning(f'Broken relation {condition=} in {skel["key"]}?!')
                continue

            # Check if one scope is in conflict, then we skip the entire condition
            # Therefore we're testing the negation of the desired scope!
            # But we only check the values that are set.
            if (condition_skel["scope_minimum_order_value"] is not None
                and condition_skel["scope_minimum_order_value"] > cart["total"]
            ):
                logger.info(f"scope_minimum_order_value not reached")
                continue

            now = utils.utcNow()
            if (condition_skel["scope_date_start"] is not None
                and condition_skel["scope_date_start"] > now
            ):
                logger.info(f"scope_date_start not reached")
                continue

            if (condition_skel["scope_date_end"] is not None
                and condition_skel["scope_date_end"] < now
            ):
                logger.info(f"scope_date_end not reached")
                continue

            if (condition_skel["scope_language"] is not None
                and condition_skel["scope_language"] != current.language.get()
            ):
                logger.info(f"scope_language not reached")
                continue

            if (condition_skel["scope_minimum_quantity"] is not None
                and condition_skel["scope_minimum_quantity"] > cart["total_quantity"]
            ):
                logger.info(f"scope_minimum_quantity not reached")
                continue

            if (condition_skel["scope_minimum_quantity"] is not None
                and condition_skel["scope_minimum_quantity"] > cart["total_quantity"]
            ):
                logger.info(f"scope_minimum_quantity not reached")
                continue

            if (condition_skel["code_type"] == CodeType.UNIVERSAL
                and condition_skel["scope_code"] == code
            ):
                logger.info(f"scope_code UNIVERSAL not reached")
                continue
            elif (condition_skel["code_type"] == CodeType.INDIVIDUAL
                  and ...
            ):
                raise NotImplementedError
                continue
            # TODO: implement all scopes
            # TODO: recheck code against this condition (any condition relation could've caused the query match!)

            # All checks are passed, we have a suitable condition
            break
        else:
            return False
        # TODO: depending on condition_operator we have to use continue or return False
        # TODO: implement combineable check

        logger.debug(f"{condition=}")

        return True
