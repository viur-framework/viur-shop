import functools
import typing as t  # noqa

from viur.core import current, db, errors, utils
from viur.core.prototypes import List
from viur.core.skeleton import SkeletonInstance, skeletonByKind
from viur.shop.types import *
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER
from ..types.dc_scope import ScopeManager

logger = SHOP_LOGGER.getChild(__name__)


class Discount(ShopModuleAbstract, List):
    kindName = "shop_discount"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "percent"
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
            applicable, cms = self.can_apply(discount_skel, cart_key, code)
            if applicable:
                logger.debug("is applicable")
                break
            else:
                for cm in cms:
                    logger.debug(f"{cm = }")
                    if cm is None:
                        logger.warning(f"[{cm=} IS NONE")
                        continue
                    for scope in cm.required_scopes:
                        if not scope.is_fulfilled:
                            logger.error(f"{scope = }")
                            # logger.error(f"{scope = } // {scope.discount_skel=} // {scope.condition_skel=} // {scope.cart_skel=}")
                        else:
                            logger.debug(f"{scope = }")


        else:
            raise errors.NotFound("No valid code found")
            return False
        logger.debug(f"Using {discount_skel=} and {cms=}")
        cms = [cm for cm in cms if cm.is_fulfilled]
        if len(domains := {cm.condition_skel["application_domain"] for cm in cms}) > 1:
            raise NotImplementedError(f"Ambiguous application_domains: {domains=}")
        cond_skel = cms[0].condition_skel
        # for cm in cms:
        #     if cm.is_fulfilled



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
        elif cond_skel["application_domain"] == ApplicationDomain.BASKET:
            if discount_skel["discount_type"] in {DiscountType.PERCENTAGE, DiscountType.ABSOLUTE}:
                cart = self.shop.cart.cart_update(
                    cart_key=cart_key,
                    discount_key=discount_skel["key"]
                )
                logger.debug(f"{cart = }")
                return {  # TODO: what should be returned?
                    "discount_skel": discount_skel,
                }
        elif cond_skel["application_domain"] == ApplicationDomain.ARTICLE:
            leaf_skels = (
                self.shop.cart.viewSkel("leaf").all()
                .filter("parentrepo =", cart_key)
                .filter("article.dest.__key__ =", cond_skel["scope_article"]["dest"]["key"])
                .fetch()
            )
            logger.debug(f"<{len(leaf_skels)}>{leaf_skels = }")
            if not leaf_skels:
                raise errors.NotFound("expected article is missing on cart")
            if len(leaf_skels) > 1:
                raise NotImplementedError("article is ambiguous")
            leaf_skel = leaf_skels[0]
            # Assign discount on new parent node for the leaf where the article is
            parent_skel = self.shop.cart.add_new_parent(leaf_skel, name=f'Discount {discount_skel["name"]}')
            cart = self.shop.cart.cart_update(
                cart_key=parent_skel["key"],
                discount_key=discount_skel["key"]
            )
            logger.debug(f"{cart = }")
            return {  # TODO: what should be returned?
                "leaf_skel": leaf_skel,
                "parent_skel": parent_skel,
                "discount_skel": discount_skel,
            }
        raise errors.NotImplemented(f'{discount_skel["discount_type"]=} is not implemented yet :(')

        return discount_skel

    def can_apply(
        self,
        skel: SkeletonInstance,
        cart_key: db.Key | None = None,
        code: str | None = None,
        as_automatically: bool = False,
    ) -> tuple[bool, list[ScopeManager]]:
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
            return False, []

        # TODO:
        """
        class ScopeCondition:
            def precondition(self, skel):#
            def is_satisfied(self, skel):#
        register from project custom
        """

        # We need the full skel with all bones (otherwise the refSkel would be to large)
        condition_skel: SkeletonInstance = skeletonByKind(skel.condition.kind)()  # noqa
        res = []
        for condition in skel["condition"]:
            if not condition_skel.fromDB(condition["dest"]["key"]):
                logger.warning(f'Broken relation {condition=} in {skel["key"]}?!')
                res.append(None)
                continue
            sm = ScopeManager()(cart_skel=cart, discount_skel=skel, condition_skel=condition_skel)
            res.append(sm)
        if skel["condition_operator"] == ConditionOperator.ONE_OF:
            if any(sm.is_fulfilled for sm in res):
                logger.debug("Any condition fulfilled")
                return True, res
            logger.debug("NOT ANY condition fulfilled")
        elif skel["condition_operator"] == ConditionOperator.ALL:
            if all(sm.is_fulfilled for sm in res):
                logger.debug("All conditions fulfilled")
                return True, res
            logger.debug("NOT ALL condition fulfilled")
        else:
            raise InvalidStateError(f'Invalid condition operator: {skel["condition_operator"]}')
        return False, res

        '''
        for condition in skel["condition"]:
            if not condition_skel.fromDB(condition["dest"]["key"]):
                logger.warning(f'Broken relation {condition=} in {skel["key"]}?!')
                continue

            # Check if one scope is in conflict, then we skip the entire condition
            # Therefore we're testing the negation of the desired scope!
            # But we only check the values that are set.
            if (
                cart is not None  # TODO
                and condition_skel["scope_minimum_order_value"] is not None
                and condition_skel["scope_minimum_order_value"] > cart["total"]
            ):
                logger.info(f"scope_minimum_order_value not reached")
                continue

            now = utils.utcNow()
            if (
                condition_skel["scope_date_start"] is not None
                and condition_skel["scope_date_start"] > now
            ):
                logger.info(f"scope_date_start not reached")
                continue

            if (
                condition_skel["scope_date_end"] is not None
                and condition_skel["scope_date_end"] < now
            ):
                logger.info(f"scope_date_end not reached")
                continue

            if (condition_skel["scope_language"] is not None
                and condition_skel["scope_language"] != current.language.get()
            ):
                logger.info(f"scope_language not reached")
                continue

            if (
                cart is not None
                and condition_skel["scope_minimum_quantity"] is not None
                and condition_skel["scope_minimum_quantity"] > cart["total_quantity"]
            ):
                logger.info(f"scope_minimum_quantity not reached")
                continue

            # TODO: if not scope_combinable_other_discount and article.shop_current_discount is not None

            if (
                condition_skel["code_type"] == CodeType.UNIVERSAL
                and condition_skel["scope_code"] != code
            ):
                logger.info(f'scope_code UNIVERSAL not reached ({condition_skel["scope_code"]=} != {code=})')
                continue
            elif (
                condition_skel["code_type"] == CodeType.INDIVIDUAL
            ):
                sub = (
                    self.shop.discount_condition.viewSkel().all()
                    .filter("parent_code.dest.__key__ =", condition_skel["key"])
                    .getSkel()
                )
                logger.debug(f"{sub = }")
                if sub["quantity_used"] > 0:
                    logger.info(f'code_type INDIVIDUAL not reached (sub already used)')
                    continue
            # TODO: implement all scopes
            # TODO: recheck code against this condition (any condition relation could've caused the query match!)

            # All checks are passed, we have a suitable condition
            break
        else:
            return False, None
        # TODO: depending on condition_operator we have to use continue or return False
        # TODO: implement combineable check
        '''

        logger.debug(f"{condition=}")

        return True, condition_skel

    @property
    @functools.cache
    def current_automatically_discounts(self):
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
