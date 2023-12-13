from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class Discount(ShopModuleAbstract, List):
    kindName = "shop_discount"
