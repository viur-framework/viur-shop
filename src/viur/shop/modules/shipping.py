from viur.core.prototypes import List
from .abstract import ShopModuleAbstract

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Shipping(ShopModuleAbstract, List):
    kindName = "shop_shipping"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "truck"
        return admin_info
