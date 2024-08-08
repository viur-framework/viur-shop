from viur.core import db, errors
from viur.core.prototypes import List

from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Vat(ShopModuleAbstract, List):
    kindName = "shop_vat"

    default_order = ("rate", db.SortOrder.Ascending)

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "cash-stack"
        return admin_info

    def get_vat_by_value(self, vat_percent: float) -> db.Key:
        if not (skel := self.viewSkel().all().mergeExternalFilter({"rate": vat_percent}).getSkel()):
            raise errors.NotFound("Vat not found")
        return skel
