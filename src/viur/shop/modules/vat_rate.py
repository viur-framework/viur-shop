from viur.core import db
from viur.core.prototypes import List

from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class VatRate(ShopModuleAbstract, List):
    moduleName = "vat_rate"
    kindName = "{{viur_shop_modulename}}_vat_rate"

    # default_order = ("country", db.SortOrder.Ascending)

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "cash-stack"
        return admin_info
