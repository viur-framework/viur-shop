import typing as t

from viur.core import current, db
from viur.core.prototypes import List
from viur.core.prototypes.skelmodule import DEFAULT_ORDER_TYPE
from viur.core.skeleton import SkeletonInstance
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER
from viur.core.prototypes.skelmodule import ORDER_TYPE

logger = SHOP_LOGGER.getChild(__name__)


class Address(ShopModuleAbstract, List):
    kindName = "shop_address"

    default_order: DEFAULT_ORDER_TYPE = (  #
        # TODO: https://github.com/viur-framework/viur-core/pull/1109
        ("firstname", db.SortOrder.Ascending)  # ,
        # ("lastname", db.SortOrder.Ascending),
    )

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "person-vcard"
        return admin_info

    def canAdd(self) -> bool:
        return True

    def listFilter(self, query: db.Query) -> t.Optional[db.Query]:
        # The current customer is only allowed to see his own addresses
        if (user := current.user.get()) and self.render.kind == "json":
            query.filter("customer.dest.__key__ =", user["key"])
            query.filter("cloned_from =", None)

        if user and (f"{self.moduleName}-view" in user["access"] or "root" in user["access"]):
            return query

        return None

    def onAdded(self, skel: SkeletonInstance):
        super().onAdded(skel)
        self._disable_old_default(skel)

    def onEdited(self, skel: SkeletonInstance):
        super().onEdited(skel)
        self._disable_old_default(skel)

    def _disable_old_default(self, skel: SkeletonInstance) -> None:
        """Disable old is_default"""
        if not skel["is_default"] or not skel["address_type"]:
            return
        query = self.editSkel().all() \
            .filter("is_default =", True) \
            .filter("customer.dest.__key__ =", skel["customer"]["dest"]["key"]) \
            .filter("address_type =", skel["address_type"].value)
        for other_skel in query.fetch(100):
            if skel["key"] != other_skel["key"]:
                other_skel["is_default"] = False
                other_skel.toDB()


Address.json = True
