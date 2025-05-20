import collections
import itertools
import typing as t

from viur.core import db, errors
from viur.core.prototypes import List
from viur.core.skeleton import RefSkel
from viur.shop.skeletons import ArticleAbstractSkel, CartNodeSkel, ShippingSkel
from viur.shop.types import SkeletonInstance_T
from .abstract import ShopModuleAbstract
from .. import SENTINEL
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Shipping(ShopModuleAbstract, List):
    moduleName = "shipping"
    kindName = "{{viur_shop_modulename}}_shipping"

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "truck"
        return admin_info

    def choose_shipping_skel_for_article(
        self,
        article_skel: SkeletonInstance_T[ArticleAbstractSkel],
        *,
        country: str | None = None,
    ) -> SkeletonInstance_T[ShippingSkel] | None | t.Literal[False]:
        """
        Chooses always the cheapest, applicable shipping for an article

        Ignores the supplier

        :param country: Ignore the context and get shipping for this country.

        # TODO(discuss): List all options?
        """
        if not article_skel["shop_shipping_config"]:
            logger.debug(f'{article_skel["key"]} has no shop_shipping_config set.')  # TODO: fallback??
            return None

        shipping_config_skel = article_skel["shop_shipping_config"]["dest"]
        # logger.debug(f"{shipping_config_skel=}")

        applicable_shippings = []
        for shipping in shipping_config_skel["shipping"]:
            is_applicable, reason = self.shop.shipping_config.is_applicable(
                shipping["dest"], shipping["rel"], article_skel=article_skel,
                country=country)
            # logger.debug(f"{shipping=} --> {is_applicable=} | {reason=}")
            if is_applicable:
                applicable_shippings.append(shipping)

        # logger.debug(f"<{len(applicable_shippings)}>{applicable_shippings=}")
        if not applicable_shippings:
            logger.error("No suitable shipping found")  # TODO: fallback??
            return False

        cheapest_shipping = min(applicable_shippings, key=lambda shipping: shipping["dest"]["shipping_cost"] or 0)
        # logger.debug(f"{cheapest_shipping=}")
        return cheapest_shipping

    def get_shipping_skels_for_cart(
        self,
        *,
        cart_key: db.Key = SENTINEL,
        cart_skel: SkeletonInstance_T[CartNodeSkel] = SENTINEL,
        country: str | None = None,
        use_cache: bool = False,
    ) -> list[SkeletonInstance_T[ShippingSkel]]:
        """Get all configured and applicable shippings of all items in the cart

        # TODO: how do we handle free shipping discounts?

        :param cart_key: Key of the parent cart node, can be a sub-cart too
        :param country: Ignore the context and get shipping for this country.
        :return: A list of :class:`SkeletonInstance`s for the :class:`ShippingSkel`.
        """
        if not ((cart_key is SENTINEL) ^ (cart_skel is SENTINEL)):
            raise ValueError("You must provide cart_key xor cart_skel")
        if cart_key is not SENTINEL:
            cart_skel = self.shop.cart.viewSkel("node")
            if not cart_skel.read(cart_key):
                raise errors.NotFound
        else:
            assert cart_skel is not SENTINEL
            cart_key = cart_skel["key"]

        if use_cache:
            get_children = self.shop.cart.get_children_from_cache
        else:
            get_children = self.shop.cart.get_children

        all_shipping_configs: list[RefSkel] = []
        # Walk down the entire cart tree and collect leafs in
        # `all_shipping_configs` and add nodes to the `node_queue`.
        node_queue = collections.deque([cart_key])
        while node_queue:
            for child in get_children(node_queue.pop()):
                if issubclass(child.skeletonCls, CartNodeSkel):
                    node_queue.append(child["key"])
                elif child.article_skel["shop_shipping_config"] is not None:
                    all_shipping_configs.append(child.article_skel["shop_shipping_config"]["dest"])

        # logger.debug(f"(before de-duplication) <{len(all_shipping_configs)}>{all_shipping_configs=}")
        # eliminate duplicates
        all_shipping_configs = list(({sc["key"]: sc for sc in all_shipping_configs}).values())
        # logger.debug(f"(after de-duplication) <{len(all_shipping_configs)}>{all_shipping_configs=}")

        if not all_shipping_configs:
            logger.debug(f'{cart_key=!r}\'s articles have no shop_shipping_config set.')  # TODO: fallback??
            return []

        all_shipping = itertools.chain.from_iterable(
            shipping_config_skel["shipping"] or []
            for shipping_config_skel in all_shipping_configs
        )

        applicable_shippings: list[SkeletonInstance_T[ShippingSkel]] = []
        for shipping in all_shipping:
            is_applicable, reason = self.shop.shipping_config.is_applicable(
                shipping["dest"], shipping["rel"], cart_skel=cart_skel,
                country=country)
            # logger.debug(f"{shipping=} --> {is_applicable=} | {reason=}")
            if is_applicable:
                applicable_shippings.append(shipping)

        # This is a workaround since we does not have a zip_code exclude list. # TODO
        # If we found any shipping for only the current zip code, we show only shippings with zip_codes.
        assert cart_skel is not None
        shipping_address = cart_skel and cart_skel["shipping_address"] and cart_skel["shipping_address"]["dest"]
        has_zip_shipping = []
        if shipping_address:
            for shipping in applicable_shippings:
                rel = shipping["rel"]
                if rel["zip_code"] and shipping_address["zip_code"] in rel["zip_code"]:
                    has_zip_shipping.append(shipping)

        if has_zip_shipping:
            logger.debug(f"Found {len(has_zip_shipping)} special zip shippings, return only these!")
            return has_zip_shipping

        # logger.debug(f"<{len(applicable_shippings)}>{applicable_shippings=}")
        if not applicable_shippings:
            logger.error("No suitable shipping found")  # TODO: fallback??
            return []

        # TODO(discuss): cheapest of each supplier?
        return applicable_shippings
