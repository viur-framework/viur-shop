import typing as t

from viur import toolkit
from viur.core.prototypes import List
from viur.core.skeleton import SkeletonInstance
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Shipping(ShopModuleAbstract, List):
    kindName = "{{viur_shop_modulename}}_shipping"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "truck"
        return admin_info

    def choose_shipping_skel_for_article(
        self,
        article_skel: SkeletonInstance
    ) -> SkeletonInstance | None | t.Literal[False]:
        logger.debug(f'choose_shipping_skel_for_article({article_skel["key"]=} | {article_skel["shop_shipping_config"]=} | )')

        if not article_skel["shop_shipping_config"]:
            logger.debug(f'{article_skel["key"]} has no shop_shipping set.')  # TODO: fallback??
            return None

        shipping_config_skel = toolkit.get_full_skel_from_ref_skel(article_skel["shop_shipping_config"]["dest"])
        logger.debug(f"{shipping_config_skel=}")

        applicable_shippings = []
        for shipping in shipping_config_skel["shipping"]:
            logger.debug(f"{shipping=}")
            is_applicable, reason = self.shop.shipping_config.is_applicable(
                shipping["dest"], shipping["rel"], article_skel, None)
            logger.debug(f"{shipping=} --> {is_applicable=} | {reason=}")
            if is_applicable:
                applicable_shippings.append(shipping)

        logger.debug(f"{applicable_shippings=}")
        if not applicable_shippings:
            logger.error("No suitable shipping found")  # TODO: fallback??
            return False

        cheapest_shipping = min(applicable_shippings, key=lambda shipping: shipping["dest"]["shipping_cost"] or 0)
        logger.debug(f"{cheapest_shipping=}")
        return cheapest_shipping
