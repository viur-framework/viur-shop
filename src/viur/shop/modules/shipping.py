from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class Shipping(ShopModuleAbstract, List):
    kindName = "shop_shipping"
