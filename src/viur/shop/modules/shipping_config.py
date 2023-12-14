import logging

from viur.core.prototypes import List
from .abstract import ShopModuleAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class ShippingConfig(ShopModuleAbstract, List):
    kindName = "shop_shipping_config"
