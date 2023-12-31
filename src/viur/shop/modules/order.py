import logging

from viur.core.prototypes import List
from .abstract import ShopModuleAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class Order(ShopModuleAbstract, List):
    kindName = "shop_order"
