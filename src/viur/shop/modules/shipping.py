import collections
import itertools
import typing as t

from viur import toolkit
from viur.core import db, errors
from viur.core.prototypes import List
from viur.core.skeleton import RefSkel, SkeletonInstance
from viur.shop.skeletons import CartNodeSkel, ShippingSkel
from viur.shop.types import SkeletonInstance_T
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
        """
        Chooses always the cheapest, applicable shipping for an article

        Ignores the supplier

        # TODO(discuss): List all options?
        """
        logger.debug(f'choose_shipping_skel_for_article({article_skel["key"]=}'
                     f' | {article_skel["shop_shipping_config"]=})')

        if not article_skel["shop_shipping_config"]:
            logger.debug(f'{article_skel["key"]} has no shop_shipping set.')  # TODO: fallback??
            return None

        shipping_config_skel = toolkit.get_full_skel_from_ref_skel(article_skel["shop_shipping_config"]["dest"])
        logger.debug(f"{shipping_config_skel=}")

        applicable_shippings = []
        for shipping in shipping_config_skel["shipping"]:
            logger.debug(f"{shipping=}")
            is_applicable, reason = self.shop.shipping_config.is_applicable(
                shipping["dest"], shipping["rel"], article_skel=article_skel)
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

    def get_shipping_skels_for_cart(
        self,
        cart_key: db.Key
    ) -> list[SkeletonInstance_T[ShippingSkel]]:
        logger.debug(f'get_shipping_skels_for_cart({cart_key=!r})')

        cart_skel = self.shop.cart.viewSkel("node")
        if not cart_skel.fromDB(cart_key):
            raise errors.NotFound

        all_shipping_configs: list[RefSkel] = []

        queue = collections.deque([cart_key])
        while queue:
            parent_cart_key = queue.pop()
            logger.debug(f"{parent_cart_key=} | {queue=}")

            for child in self.shop.cart.get_children(parent_cart_key):
                if issubclass(child.skeletonCls, CartNodeSkel):
                    logger.debug(f"{child=}")
                    queue.append(child["key"])
                    ...
                    # TODO: we ignore currently the sub card
                else:
                    logger.debug(f"{child=} | {child.article_skel=}")
                    logger.debug(f'{child.article_skel["shop_shipping_config"]=}')
                    if child.article_skel["shop_shipping_config"] is not None:
                        all_shipping_configs.append(child.article_skel["shop_shipping_config"]["dest"])

        logger.debug(f"(before de-duplication) <{len(all_shipping_configs)}>{all_shipping_configs=}")
        # eliminate duplicates
        all_shipping_configs = ({sc["key"]: sc for sc in all_shipping_configs}).values()
        logger.debug(f"(after de-duplication) <{len(all_shipping_configs)}>{all_shipping_configs=}")

        if not all_shipping_configs:
            logger.debug(f'{cart_key=!r}\'s articles have no shop_shipping_config set.')  # TODO: fallback??
            return []

        shipping_config_skels = list(map(toolkit.get_full_skel_from_ref_skel, all_shipping_configs))
        logger.debug(f"{shipping_config_skels=}")

        all_shipping = itertools.chain.from_iterable(
            shipping_config_skel["shipping"] or []
            for shipping_config_skel in shipping_config_skels
        )

        applicable_shippings: list[SkeletonInstance_T[ShippingSkel]] = []
        for shipping in all_shipping:
            logger.debug(f"{shipping=}")
            is_applicable, reason = self.shop.shipping_config.is_applicable(
                shipping["dest"], shipping["rel"], cart_skel=cart_skel)
            logger.debug(f"{shipping=} --> {is_applicable=} | {reason=}")
            if is_applicable:
                applicable_shippings.append(shipping)

        logger.debug(f"{applicable_shippings=}")
        if not applicable_shippings:
            logger.error("No suitable shipping found")  # TODO: fallback??
            return []

        # TODO(discuss): cheapest of each supplier?
        return applicable_shippings
