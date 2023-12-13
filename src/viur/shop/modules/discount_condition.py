from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class DiscountCondition(ShopModuleAbstract, List):
    kindName = "shop_discount_condition"
