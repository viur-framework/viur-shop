import logging

from viur.core.prototypes import List
from viur.core.skeleton import RefSkel, RelSkel
from viur.shop.skeletons import ArticleAbstractSkel, CartNodeSkel
from viur.shop.types import SkeletonInstance_T
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER
from ..services import HOOK_SERVICE, Hook
from ..types.exceptions import DispatchError

logger = SHOP_LOGGER.getChild(__name__)


class ShippingConfig(ShopModuleAbstract, List):
    moduleName = "shipping_config"
    kindName = "{{viur_shop_modulename}}_shipping_config"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "truck-flatbed"
        return admin_info

    def is_applicable(
        self,
        dest: RefSkel,
        rel: RelSkel,
        *,
        article_skel: SkeletonInstance_T[ArticleAbstractSkel] | None = None,
        cart_skel: SkeletonInstance_T[CartNodeSkel] | None = None,
        country: str | None = None,
    ) -> tuple[bool, str]:
        """
        Check if a shipping configuration is applicable in the current context.

        Provide eiter `article_skel` for single article context
        xor `cart_skel` for cart context.

        :param country: If provided, check if the shipping configuration is applicable for this country.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'is_applicable({dest=}, {rel=}, '
                         f'{article_skel and article_skel["key"]=!r}, '
                         f'{cart_skel=}, {country=})')

        if not ((article_skel is None) ^ (cart_skel is None)):
            raise ValueError("You must supply article_skel or cart_skel")

        if rel["minimum_order_value"]:
            if cart_skel is None:
                if (article_skel.shop_price_.current or 0) < rel["minimum_order_value"]:
                    return False, "< minimum_order_value [article]"
            else:
                if cart_skel["total_raw"] < rel["minimum_order_value"]:
                    return False, "< minimum_order_value [cart]"

        shipping_address = cart_skel and cart_skel["shipping_address"] and cart_skel["shipping_address"]["dest"]

        if rel["country"]:
            use_country: str | None = None
            if country is not None:
                use_country = country
            elif article_skel is not None:
                try:
                    use_country = HOOK_SERVICE.dispatch(Hook.CURRENT_COUNTRY)("article")
                except DispatchError:
                    logger.info("NOTE: This error can be eliminated by providing "
                                "a `Hook.CURRENT_COUNTRY` customization.")
                    return False, "cannot apply country on article_skel"
            elif cart_skel is not None and shipping_address:
                use_country = shipping_address["country"]
            elif cart_skel is not None and not shipping_address:
                try:
                    use_country = HOOK_SERVICE.dispatch(Hook.CURRENT_COUNTRY)("cart")
                except DispatchError:
                    logger.info("NOTE: This error can be eliminated by providing "
                                "a `Hook.CURRENT_COUNTRY` customization.")
                    return False, "cannot apply country on cart_skel without shipping_address and Hook.CURRENT_COUNTRY"
            logger.debug(f'[CHECK] {use_country=} in {rel["country"]=} ? :: {use_country in rel["country"]}')
            if use_country not in rel["country"]:
                return False, f'{use_country=} not in {rel["country"]=}'

        if rel["zip_code"]:
            if article_skel is not None:
                return False, "cannot apply zip_code on article_skel"
            elif cart_skel is not None and not shipping_address:
                return False, "cannot apply zip_code on cart_skel without shipping_address"
            elif cart_skel is not None:
                if shipping_address["zip_code"] not in rel["zip_code"]:
                    return False, f'{shipping_address["zip_code"]=} not in {rel["zip_code"]=}'

        return True, ""
