import pprint
import random
import string
import typing as t

from viur import toolkit
from viur.core import current, db, tasks
from viur.core.prototypes import List
from viur.core.skeleton import SkeletonInstance
from .abstract import ShopModuleAbstract
from ..globals import SHOP_INSTANCE, SHOP_LOGGER
from ..services import Event, on_event
from ..types import CodeType

logger = SHOP_LOGGER.getChild(__name__)

CODE_CHARS = sorted(set(string.ascii_letters + string.digits).difference(set("0OIl1")))
CODE_LENGTH = 8
SUFFIX_LENGTH = 6


class DiscountCondition(ShopModuleAbstract, List):
    kindName = "shop_discount_condition"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "percent"
        admin_info["filter"] = {
            "is_subcode": False,
            "orderby": "name",
        }
        admin_info["editViews"] = [
            {
                "module": "shop/discount",
                "name": "Discounts using this condition",
                "context": "condition.dest.key",
                "filter": {
                    # "is_subcode": True,
                    # "orderby": "scope_code",
                },
                # "columns": ["scope_code", "quantity_used"],
            },
            {
                "module": "shop/discount_condition",
                "name": "Sub Codes",
                "context": "parent_code.dest.key",
                "filter": {
                    "is_subcode": True,
                    "orderby": "scope_code",
                },
                "columns": ["scope_code", "quantity_used"],
            },
        ]
        return admin_info

    # --- Generation / admin logic --------------------------------------------

    def canEdit(self, skel):
        if skel["is_subcode"]:
            return False
        if skel["code_type"] is not None and skel["code_type"] != CodeType.NONE:
            skel.code_type.readOnly = True
        return super().canEdit(skel)

    def editSkel(self, *args, **kwargs) -> SkeletonInstance:
        skel = super().editSkel().ensure_is_cloned()
        skel.individual_codes_prefix.readOnly = True
        # skel.code_type.readOnly = True
        skel.individual_codes_prefix.readOnly = True
        return skel

    def onAdd(self, skel: SkeletonInstance):
        super().onAdd(skel)
        self.on_change(skel, "add")

    def onEdit(self, skel: SkeletonInstance):
        super().onEdit(skel)
        self.on_change(skel, "edit")

    def onAdded(self, skel: SkeletonInstance):
        super().onAdded(skel)
        self.on_changed(skel, "added")

    def onEdited(self, skel: SkeletonInstance):
        super().onEdited(skel)
        self.on_changed(skel, "edited")

    def on_change(self, skel, event: str):
        logger.debug(pprint.pformat(skel, width=120))
        skel_old = self.viewSkel()
        if skel["key"] is not None:  # not on add
            skel_old.fromDB(skel["key"])
        current.request_data.get()[f'shop_skel_{skel["key"]}'] = skel_old

    def on_changed(self, skel, event: str):
        logger.debug(pprint.pformat(skel, width=120))
        if skel["code_type"] == CodeType.INDIVIDUAL and not skel["is_subcode"]:
            skel_old = current.request_data.get()[f'shop_skel_{skel["key"]}']
            query = self.viewSkel().all().filter("parent_code.dest.__key__ =", skel["key"])
            counter = query.count()
            logger.debug(f"{counter = }")
            if skel["individual_codes_amount"] > counter:
                self.generate_subcodes(skel["key"], skel["individual_codes_prefix"],
                                       skel["individual_codes_amount"] - counter)

    @tasks.CallDeferred
    def generate_subcodes(self, parent_key: db.Key, prefix: str, amount: int):
        """Generate subcodes for a parent individual code."""
        chunk_amount = amount
        while chunk_amount > 0:
            skel = self.addSkel()  # .subSkel("individual")
            skel["is_subcode"] = True
            skel["quantity_volume"] = 1
            skel.setBoneValue("parent_code", parent_key)

            _try = 1
            while True:
                skel["scope_code"] = "".join(
                    (prefix, "".join(random.choice(CODE_CHARS) for _ in range(SUFFIX_LENGTH))))

                try:
                    self.onAdd(skel)
                    skel.toDB()
                    self.onAdded(skel)
                    break
                except ValueError as e:
                    if "The unique value" in str(e):
                        if _try == 30:
                            logger.error(f"Try %d failed. Terminate generation.", _try)
                            raise

                        logger.error(f"Code %r is already forgiven. This was try: %d", skel["scope_code"], _try)
                        _try += 1
                    else:
                        raise

            chunk_amount -= 1

            if amount - chunk_amount == 50:
                self.generate_subcodes(parent_key, prefix, chunk_amount)
                return

        logger.info(f"Finished code generation for {parent_key} ({prefix=}).")

    # --- Apply logic ---------------------------------------------------------

    def get_by_code(self, code: str = None) -> t.Iterator[SkeletonInstance]:
        query = self.viewSkel().all().filter("scope_code =", code)
        for cond_skel in query.fetch(100):
            if cond_skel["is_subcode"]:
                parent_cond_skel = self.viewSkel()
                assert parent_cond_skel.fromDB(cond_skel["parent_code"]["dest"]["key"])
                yield parent_cond_skel
                # yield cond_skel["parent_code"]["dest"]
            else:
                yield cond_skel

    def get_discounts_from_cart(self, cart_key: db.Key) -> list[db.Key]:
        nodes = self.shop.cart.viewSkel("node").all().filter("parentrepo =", cart_key).fetch(100)
        discounts = []
        for node in nodes:
            logger.debug(f"{node = }")
            if node["discount"]:
                discounts.append(node["discount"]["dest"]["key"])
        # TODO: collect used from price and automatically as well
        return discounts

    @on_event(Event.ORDER_ORDERED)
    @staticmethod
    def mark_discount_used(order_skel, payment):
        """Increase quantity_used on discount of an ordered cart"""
        logger.info(f"Calling mark_discount_used with {order_skel=} {payment=}")
        self = SHOP_INSTANCE.get().discount_condition
        discounts = self.get_discounts_from_cart(order_skel["cart"]["dest"]["key"])
        logger.debug(f"{discounts = }")

        for discount in discounts:
            d_skel = self.shop.discount.viewSkel()
            d_skel.fromDB(discount)
            for condition in d_skel["condition"]:
                # TODO: Increase only "active" conditions in case of OR operator
                # cond_skel = toolkit.get_full_skel_from_ref_skel(condition["dest"])
                res = toolkit.increase_counter(condition["dest"]["key"], "quantity_used", 1)
                logger.debug(f"old value: {res = }")
