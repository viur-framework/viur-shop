from viur.core.prototypes import List
from .abstract import ShopModuleAbstract


class ShippingConfig(ShopModuleAbstract, List):
    kindName = "shop_shipping_config"
