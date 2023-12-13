from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class Order(ShopModuleAbstract, List):
    kindName = "shop_order"
