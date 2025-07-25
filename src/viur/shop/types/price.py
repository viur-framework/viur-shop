"""
Price calculation module for the viur-shop plugin.

This module provides the `Price` class, which encapsulates logic for computing
product prices, VAT handling, and applying various discounts for articles or cart items
within the viur-shop system. It supports both static article pricing and dynamic pricing
based on cart state and active discount campaigns.

Core functionality includes:

-   Retail, recommended, and current (discounted) price calculations.
-   Net/gross price conversions including VAT.
-   Evaluation of applicable discounts from both article and cart context.
-   Price serialization for frontend/API consumption.
-   Request-local price caching to optimize performance.
"""

import functools
import json
import typing as t  # noqa

from viur import toolkit
from viur.core import current, db, utils
from viur.core.skeleton import SkeletonInstance
from .enums import ApplicationDomain, ConditionOperator, DiscountType
from .exceptions import InvalidStateError
from ..globals import SHOP_INSTANCE, SHOP_LOGGER
from ..types import ConfigurationError, DiscountValidationContext

if t.TYPE_CHECKING:
    from ..modules import Discount

logger = SHOP_LOGGER.getChild(__name__)

# TODO: Use decimal package instead of floats?
#       -> decimal mode in NumericBone?

PRICE_PRECISION: t.Final[int] = 2
"""Precision, how many digits are used to round prices"""


class Price:
    """
    Represents the pricing logic and applicable discounts for an article or cart item.

    This class handles price calculation for shop articles, taking into account the current
    discounts, whether the item is in the cart, VAT, and other relevant conditions.

    It supports retail and recommended prices (gross/net), discount combinations, and tracks
    savings both in value and percentage. It also provides a method to return all pricing data
    as a dictionary for serialization.
    """

    cart_discounts: list[SkeletonInstance] = []
    article_discount: SkeletonInstance = None

    is_in_cart = None
    article_skel = None
    cart_leaf = None

    def __init__(self, src_object: SkeletonInstance):
        """
        Initialize a Price object based on an article or cart item skeleton.
        Sets up the article reference, detects cart state, and loads applicable discounts.

        :param src_object: Either an article skeleton or a cart item skeleton.
        :raises TypeError: If `src_object` is not a supported type.
        :raises InvalidStateError: If the article skeleton has already run renderPreparation.
        """
        super().__init__()
        # logger.debug(f"Creating new price object based on {src_object=}")
        shop = SHOP_INSTANCE.get()
        if isinstance(src_object, SkeletonInstance) and issubclass(src_object.skeletonCls, shop.cart.leafSkelCls):
            self.is_in_cart = True
            self.cart_leaf = src_object
            self.article_skel = toolkit.without_render_preparation(src_object.article_skel_full)
            try:
                self.cart_discounts = shop.cart.get_discount_for_leaf(src_object)
            except Exception as exc:  # FIXME: some entities are broken?
                logger.exception(exc)
                self.cart_discounts = []
            self.cart_discounts = [toolkit.get_full_skel_from_ref_skel(d) for d in self.cart_discounts]
        elif isinstance(src_object, SkeletonInstance) and issubclass(src_object.skeletonCls, shop.article_skel):
            self.is_in_cart = False
            self.article_skel = toolkit.without_render_preparation(src_object)
        else:
            raise TypeError(f"Unsupported type {type(src_object)}")

        # logger.debug(f"{self.article_skel = }")
        # logger.debug(f"{self.article_skel.renderPreparation=} | {hex(id(self.article_skel))}")
        if self.article_skel.renderPreparation is not None:
            raise InvalidStateError("ArticleSkel must not have renderPreparation")

        if (best_discount := self.shop_current_discount(self.article_skel)) is not None:
            price, skel = best_discount
            self.article_discount = skel
            # self.cart_discounts.insert(0, skel)  # the general shop discount without a code

    @property
    def retail(self) -> float:
        """
        Returns the retail (normal) gross price of the article.

        :return: Gross retail price as float.
        """
        return self.article_skel["shop_price_retail"]

    @property
    def retail_net(self) -> float:
        """
        Calculates the net value from the retail price based on VAT.

        :return: Retail price without VAT.
        """
        return toolkit.round_decimal(self.gross_to_net(self.retail, self.vat_rate_percentage), PRICE_PRECISION)

    @property
    def recommended(self) -> float:
        """
        Returns the recommended retail price (RRP) as set in the article.

        :return: Recommended gross price.
        """
        return self.article_skel["shop_price_recommended"]

    @property
    def recommended_net(self) -> float:
        """
        Returns the net version of the recommended price.

        :return: Net recommended price.
        """
        return toolkit.round_decimal(self.gross_to_net(self.recommended, self.vat_rate_percentage), PRICE_PRECISION)

    @property
    def saved(self) -> float:
        """
        Calculates how much is saved compared to the retail price.

        :return: Absolute savings in currency units.
        """
        if self.retail is None or self.current is None:
            return 0
        return toolkit.round_decimal(self.retail - self.current, PRICE_PRECISION)

    @property
    def saved_net(self) -> float:
        """
        Calculates the net value of the saved amount.

        :return: Net savings amount.
        """
        return toolkit.round_decimal(self.gross_to_net(self.saved, self.vat_rate_percentage), PRICE_PRECISION)

    @property
    def saved_percentage(self) -> float:
        """
        Returns how much the customer saves as a percentage of the retail price.

        :return: Savings percentage (0.0 - 1.0).
        """
        try:
            return toolkit.round_decimal(self.saved / self.retail, PRICE_PRECISION)
        except (ZeroDivisionError, TypeError):  # One value is None
            return 0.0

    # @property
    @functools.cached_property
    def current(self) -> float:
        """
        Computes the final current price after applying all applicable discounts.

        :return: Final discounted price.
        """
        if (not self.is_in_cart or not self.cart_discounts) and self.article_discount:
            # only the article_discount is applicable
            return toolkit.round_decimal(self.apply_discount(self.article_discount, self.retail), PRICE_PRECISION)
        if self.is_in_cart and self.cart_discounts:
            # TODO: if self.article_discount:
            best_price, best_discounts = self.choose_best_discount_set()
            return toolkit.round_decimal(best_price, PRICE_PRECISION)
        return self.retail

    @property
    def current_net(self) -> float:
        """
        Returns the net value of the current (discounted) price.

        :return: Current price without VAT.
        """
        return toolkit.round_decimal(self.gross_to_net(self.current, self.vat_rate_percentage), PRICE_PRECISION)

    def shop_current_discount(self, article_skel: SkeletonInstance) -> None | tuple[float, "SkeletonInstance"]:
        """
        Find the best automatic (permanent) discount currently available for the article.

        :param article_skel: The article skeleton to check.
        :return: Tuple of (discounted price, discount skeleton) or None if no discounts apply.
        """
        best_discount = None
        article_price = self.retail or 0.0  # FIXME(discuss): how to handle None prices?
        if not article_price:
            return None
        discount_module: "Discount" = SHOP_INSTANCE.get().discount
        for skel in SHOP_INSTANCE.get().discount.current_automatically_discounts:
            applicable, dv = discount_module.can_apply(
                skel, article_skel=article_skel,
                context=DiscountValidationContext.AUTOMATICALLY_LIVE
            )
            # logger.debug(f"{dv=}")
            if not applicable:
                logger.debug(f'{skel["name"]} is NOT applicable')
                continue
            price = self.apply_discount(skel, article_price)
            if best_discount is None or price < best_discount[0]:
                best_discount = price, skel
        return best_discount

    def choose_best_discount_set(self) -> tuple[float, list[SkeletonInstance]]:
        """
        Find the best combination of applicable cart discounts for the article.

        :return: Tuple of (best price, list of discount skeletons applied).
        """
        # TODO: consider self.article_discount
        all_permutations = [[d] for d in self.cart_discounts]
        combinables = []
        """ALl discounts which are combineable together"""
        for discount in self.cart_discounts:
            # Collect all combineable discounts as one permutation
            # logger.debug(f"{discount=}")
            if discount["condition_operator"] == ConditionOperator.ALL \
                and all(c["dest"]["scope_combinable_other_discount"] for c in discount["condition"]):
                combinables.append(discount)
            elif discount["condition_operator"] == ConditionOperator.ONE_OF \
                and len(discount["condition"]) == 1:
                combinables.append(discount)
            elif discount["condition_operator"] == ConditionOperator.ONE_OF \
                and any(c["dest"]["scope_combinable_other_discount"] for c in discount["condition"]):
                logger.warning("#TODO: this case is tricky")  # TODO: this case is tricky
                combinables.append(discount)
            else:
                logger.info(f"Not suitable for combinables")
                continue
        all_permutations.append(combinables)
        best_price = self.retail
        best_discounts = None
        for permutation in all_permutations:
            price = self.retail  # start always from the retail price
            for discount in permutation:
                # only add if ApplicationDomain.ARTICLE
                if any(
                    condition["dest"]["application_domain"] == ApplicationDomain.ARTICLE
                    for condition in discount["condition"]
                ):
                    price = self.apply_discount(discount, price)
            if price < best_price:  # Is this discount better?
                best_price = price
                best_discounts = permutation

        return best_price, best_discounts

    # @property
    @functools.cached_property
    def vat_rate_percentage(self) -> float:
        """
        Returns the VAT rate as a float for this article (e.g. 0.19 for 19 %).

        :return: VAT rate as float between 0.0 and 1.0.
        """
        try:
            country = self._shipping_address["dest"]["country"]
        except (KeyError, TypeError):
            country = None
        # logger.debug(f"Using country: {country}")
        try:
            # FIXME: self.article_skel has here sometimes renderPreparation set,
            #        but toolkit.without_render_preparation is already called in __init__
            #        What's going on here?
            vat_rate = SHOP_INSTANCE.get().vat_rate.get_vat_rate_for_country(
                country=country,
                category=toolkit.without_render_preparation(self.article_skel)["shop_vat_rate_category"],
            )
        except ConfigurationError as e:  # TODO(discussion): Or re-raise or implement fallback?
            logger.warning(f"No vat rate for article :: {e}")
            vat_rate = 0.0
        return (vat_rate or 0.0) / 100

    @property
    def vat_included(self) -> float:
        """
        Calculates the VAT amount included in the current price.

        :return: Included VAT value.
        """
        try:
            return toolkit.round_decimal(self.gross_to_vat(self.current, self.vat_rate_percentage), PRICE_PRECISION)
        except TypeError:  # One value is None
            return 0.0

    @functools.cached_property
    def _shipping_address(self):
        """
        Returns the shipping address for the closest cart node.
        """
        if not self.is_in_cart:
            return None
        res = SHOP_INSTANCE.get().cart.get_closest_node(
            self.cart_leaf,
            condition=lambda skel: skel["shipping_address"] is not None,
        )
        if res:
            return res["shipping_address"]
        return res

    def to_dict(self) -> dict:
        """
        Serializes the relevant pricing fields to a dictionary, suitable for frontend or API use.

        :return: Dictionary with pricing information and discounts.
        """
        from viur.shop.types import ExtendedCustomJsonEncoder
        return {
            attr_name: getattr(self, attr_name)
            for attr_name, attr_value in vars(self.__class__).items()
            if isinstance(attr_value, (property, functools.cached_property)) and not attr_name.startswith("_")
        } | utils.json.loads(json.dumps({  # must be JSON serializable for vi renderer
            "cart_discounts": self.cart_discounts,
            "article_discount": self.article_discount,
        }, cls=ExtendedCustomJsonEncoder))

    @staticmethod
    def apply_discount(
        discount_skel: SkeletonInstance,
        article_price: float
    ) -> float:
        """
        Applies a given discount to a given article price.

        :param discount_skel: Discount skeleton to apply.
        :param article_price: Base price of the article.
        :return: New price after applying the discount.
        :raises NotImplementedError: If the discount type is not supported.
        """
        if discount_skel["discount_type"] == DiscountType.FREE_ARTICLE:
            return 0.0
        elif discount_skel["discount_type"] == DiscountType.ABSOLUTE:
            price = article_price - discount_skel["absolute"]
        elif discount_skel["discount_type"] == DiscountType.PERCENTAGE:
            price = article_price - (
                article_price * discount_skel["percentage"] / 100
            )
        else:
            logger.info(f"NotSupported discount: {discount_skel=}")
            raise NotImplementedError
        return price

    @staticmethod
    def gross_to_net(gross_value: float, vat_value: float) -> float:
        """
        Converts a gross price to net using the given VAT rate.

        :param gross_value: Gross price.
        :param vat_value: VAT rate (0.0 - 1.0).
        :return: Net price.
        :raises ValueError: If VAT value is out of range.
        """
        if not (0 <= vat_value <= 1):
            raise ValueError(f"Invalid vat value: {vat_value}")
        if not gross_value:
            return 0.0
        return gross_value / (1 + vat_value)

    @staticmethod
    def gross_to_vat(gross_value: float, vat_value: float) -> float:
        """
        Extracts the VAT amount from a gross value.

        :param gross_value: Gross price.
        :param vat_value: VAT rate (0.0 - 1.0).
        :return: VAT amount.
        :raises ValueError: If VAT value is out of range.
        """
        if not (0 <= vat_value <= 1):
            raise ValueError(f"Invalid vat value: {vat_value}")
        if not gross_value:
            return 0.0
        return Price.gross_to_net(gross_value, vat_value) * vat_value

    @classmethod
    def get_or_create(cls, src_object) -> t.Self:
        """
        Returns a cached or newly created Price object for the given article or cart item.

        Caches the result in the current request context for reuse.

        :param src_object: Source article or cart item skeleton.
        :return: Price instance.
        """
        # logger.debug(f"Called get_or_create with {src_object = }")
        try:
            obj = cls.get_cache()[src_object["key"]]
            logger.debug(f'Price.get_or_create() hit cache for {src_object["key"]}')
            return obj
        except KeyError:
            pass
        obj = Price(src_object)
        cls.get_cache()[src_object["key"]] = obj
        return obj

    @classmethod
    def get_cache(cls) -> dict[db.Key, t.Self]:
        """
        Request-local price cache to avoid recalculating prices during one request lifecycle.

        :return: Dictionary keyed by skeleton key, with cached `Price` objects.
        """
        return current.request_data.get().setdefault("viur.shop", {}).setdefault("price_cache", {})
