from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class Vat(ShopModuleAbstract, List):
    kindName = "shop_vat"
