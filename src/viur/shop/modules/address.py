import logging
import typing as t

from viur.core import current, db
from viur.core.prototypes import List
from viur.core.skeleton import SkeletonInstance
from .abstract import ShopModuleAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class Address(ShopModuleAbstract, List):
    kindName = "shop_address"

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
