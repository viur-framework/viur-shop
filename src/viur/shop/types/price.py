import functools
import json
import typing as t  # noqa

from viur import toolkit
from viur.core import current, db, utils
from viur.core.skeleton import SkeletonInstance
from .enums import ApplicationDomain, ConditionOperator, DiscountType
from ..globals import SHOP_INSTANCE, SHOP_LOGGER
from ..types import ConfigurationError

if t.TYPE_CHECKING:
    from ..modules import Discount

logger = SHOP_LOGGER.getChild(__name__)

# TODO: Use decimal package instead of floats?
#       -> decimal mode in NumericBone?

PRICE_PRECISION: t.Final[int] = 2
"""Precision, how many digits are used to round prices"""


class Price:
    cart_discounts: list[SkeletonInstance] = []
    article_discount: SkeletonInstance = None

    is_in_cart = None
    article_skel = None
    cart_leaf = None

    def __init__(self, src_object):
        super().__init__()
        # logger.debug(f"Creating new price object based on {src_object=}")
        shop = SHOP_INSTANCE.get()
        if isinstance(src_object, SkeletonInstance) and issubclass(src_object.skeletonCls, shop.cart.leafSkelCls):
            self.is_in_cart = True
            self.cart_leaf = src_object
            self.article_skel = src_object.article_skel_full
            try:
                self.cart_discounts = shop.cart.get_discount_for_leaf(src_object)
            except Exception as exc:  # FIXME: some entities are broken?
                logger.exception(exc)
                self.cart_discounts = []
            self.cart_discounts = [toolkit.get_full_skel_from_ref_skel(d) for d in self.cart_discounts]
        elif isinstance(src_object, SkeletonInstance) and issubclass(src_object.skeletonCls, shop.article_skel):
            self.is_in_cart = False
            self.article_skel = src_object
        else:
            raise TypeError(f"Unsupported type {type(src_object)}")

        # logger.debug(f"{self.article_skel = }")

        if (best_discount := self.shop_current_discount(self.article_skel)) is not None:
            price, skel = best_discount
            self.article_discount = skel
            # self.cart_discounts.insert(0, skel)  # the general shop discount without a code

    @property
    def retail(self) -> float:
        return self.article_skel["shop_price_retail"]

    @property
    def retail_net(self) -> float:
        return toolkit.round_decimal(self.gross_to_net(self.retail, self.vat_rate_percentage), PRICE_PRECISION)

    @property
    def recommended(self) -> float:
        return self.article_skel["shop_price_recommended"]

    @property
    def recommended_net(self) -> float:
        return toolkit.round_decimal(self.gross_to_net(self.recommended, self.vat_rate_percentage), PRICE_PRECISION)

    @property
    def saved(self) -> float:
        if self.retail is None or self.current is None:
            return 0
        return toolkit.round_decimal(self.retail - self.current, PRICE_PRECISION)

    @property
    def saved_net(self) -> float:
        return toolkit.round_decimal(self.gross_to_net(self.saved, self.vat_rate_percentage), PRICE_PRECISION)

    @property
    def saved_percentage(self) -> float:
        try:
            return toolkit.round_decimal(self.saved / self.current, PRICE_PRECISION)
        except (ZeroDivisionError, TypeError):  # One value is None
            return 0.0

    # @property
    @functools.cached_property
    def current(self) -> float:
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
        return toolkit.round_decimal(self.gross_to_net(self.current, self.vat_rate_percentage), PRICE_PRECISION)

    def shop_current_discount(self, article_skel: SkeletonInstance) -> None | tuple[float, "SkeletonInstance"]:
        """Best permanent discount campaign for article"""
        best_discount = None
        article_price = self.retail or 0.0  # FIXME(discuss): how to handle None prices?
        if not article_price:
            return None
        discount_module: "Discount" = SHOP_INSTANCE.get().discount
        for skel in SHOP_INSTANCE.get().discount.current_automatically_discounts:
            # TODO: if can apply (article range, lang, ...)
            applicable, dv = discount_module.can_apply(skel, article_skel=article_skel, as_automatically=True)
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
        Find the best set of applyable discounts for this article.

        Returns: The best_price and the set of the applied discounts
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
        """Vat rate for the article

        :returns: value as float (0.0 <= value <= 1.0)
        """
        try:
            vat_rate = SHOP_INSTANCE.get().vat_rate.get_vat_rate_for_country(
                category=self.article_skel["shop_vat_rate_category"],
            )
        except ConfigurationError as e:  # TODO(discussion): Or re-raise or implement fallback?
            logger.warning(f"No vat rate for article :: {e}")
            vat_rate = 0.0
        return (vat_rate or 0.0) / 100

    @property
    def vat_included(self) -> float:
        """Calculate the included vat value based on current price and vat rate"""
        try:
            return toolkit.round_decimal(self.gross_to_vat(self.current, self.vat_rate_percentage), PRICE_PRECISION)
        except TypeError:  # One value is None
            return 0.0

    def to_dict(self) -> dict:
        from viur.shop.types import ExtendedCustomJsonEncoder
        return {
            attr_name: getattr(self, attr_name)
            for attr_name, attr_value in vars(self.__class__).items()
            if isinstance(attr_value, (property, functools.cached_property))
        } | utils.json.loads(json.dumps({  # must be JSON serializable for vi renderer
            "cart_discounts": self.cart_discounts,
            "article_discount": self.article_discount,
        }, cls=ExtendedCustomJsonEncoder))

    @staticmethod
    def apply_discount(
        discount_skel: SkeletonInstance,
        article_price: float
    ) -> float:
        """Apply a given discount on the given price and return the new price"""
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
        if not (0 <= vat_value <= 1):
            raise ValueError(f"Invalid vat value: {vat_value}")
        if not gross_value:
            return 0.0
        return gross_value / (1 + vat_value)

    @staticmethod
    def gross_to_vat(gross_value: float, vat_value: float) -> float:
        if not (0 <= vat_value <= 1):
            raise ValueError(f"Invalid vat value: {vat_value}")
        if not gross_value:
            return 0.0
        return Price.gross_to_net(gross_value, vat_value) * vat_value

    @classmethod
    def get_or_create(cls, src_object) -> t.Self:
        """Get a existing cached or create a new Price object for ArticleSkel or CartItemSkel and cache it"""
        # logger.debug(f"Called get_or_create with {src_object = }")
        try:
            cls.cache[src_object["key"]]
            logger.debug(f'Price.get_or_create() hit cache for {src_object["key"]}')
            return cls.cache[src_object["key"]]
        except KeyError:
            pass
        obj = Price(src_object)
        cls.cache[src_object["key"]] = obj
        return obj

    @classmethod
    @property
    def cache(cls) -> dict[db.Key, t.Self]:
        return current.request_data.get().setdefault("viur.shop", {}).setdefault("price_cache", {})
