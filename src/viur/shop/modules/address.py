from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class Address(ShopModuleAbstract, List):
    kindName = "shop_address"
