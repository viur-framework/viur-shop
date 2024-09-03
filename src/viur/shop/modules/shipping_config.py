from viur.core.prototypes import List
from .abstract import ShopModuleAbstract

from ..globals import SHOP_LOGGER
from ...core.skeleton import SkeletonInstance

logger = SHOP_LOGGER.getChild(__name__)


class ShippingConfig(ShopModuleAbstract, List):
    kindName = "{{viur_shop_modulename}}_shipping_config"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "truck-flatbed"
        return admin_info

    def is_applicable(
        self,
        dest,
        rel,
        article_skel: SkeletonInstance,  # ArticleSkel
        cart_skel: SkeletonInstance | None = None,  # CartNodeSkel
    ) -> tuple[bool, str]:
        logger.debug(f'is_applicable({dest=}, {rel=}, {article_skel and article_skel["key"]=!r}, {cart_skel=})')

        if rel["minimum_order_value"]:
            if cart_skel is None:
                if article_skel.shop_price_.current < rel["minimum_order_value"]:
                    return False, "< minimum_order_value [article]"
            else:
                if cart_skel["total"] < rel["minimum_order_value"]:
                    return False, "< minimum_order_value [cart]"

        if rel["country"]: ...  # TODO
        if rel["zip_code"]: ...  # TODO

        return True, ""
