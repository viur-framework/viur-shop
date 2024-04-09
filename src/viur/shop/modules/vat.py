from viur.core import db
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
