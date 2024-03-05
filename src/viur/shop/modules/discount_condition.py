import logging

from viur.core.prototypes import List
from .abstract import ShopModuleAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class DiscountCondition(ShopModuleAbstract, List):
    kindName = "shop_discount_condition"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "percent"
        return admin_info
