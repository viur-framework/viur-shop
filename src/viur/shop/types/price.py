import functools
import typing as t  # noqa

from viur.core import current, utils
from viur.core.skeleton import SkeletonInstance

from viur import toolkit
from .enums import ConditionOperator, DiscountType
from ..globals import SHOP_INSTANCE, SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


# TODO: Use decimal package instead of floats?
#       -> decimal mode in NumericBone?

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
        # logger.debug(f"{self.article_skel.shop_current_discount = }")

        if (best_discount := self.shop_current_discount(self.article_skel)) is not None:
            price, skel = best_discount
            self.article_discount = skel
            # self.cart_discounts.insert(0, skel)  # the general shop discount without a code

    @property
    def retail(self) -> float:
        return self.article_skel["shop_price_retail"]

    @property
    def recommended(self) -> float:
        return self.article_skel["shop_price_recommended"]

    @property
    def saved(self) -> float:
        if self.retail is None or self.current is None:
            return 0
        return toolkit.round_decimal(self.retail - self.current, 2)

    @property
    def saved_percentage(self) -> float:
        try:
            return toolkit.round_decimal(self.saved / self.current, 2 or 4)  # TODO
        except (ZeroDivisionError, TypeError):  # One value is None
            return 0.0

    # @property
    @functools.cached_property
    def current(self) -> float:
        if (not self.is_in_cart or not self.cart_discounts) and self.article_discount:
            # only the article_discount is applicable
            return toolkit.round_decimal(self.apply_discount(self.article_discount, self.retail), 2)
        if self.is_in_cart and self.cart_discounts:
            # TODO: if self.article_discount:
            best_price, best_discounts = self.choose_best_discount_set()
            return toolkit.round_decimal(best_price, 2)
        return self.retail

    def shop_current_discount(self, skel) -> None | tuple[float, "SkeletonInstance"]:
        """Best permanent discount campaign for article"""
        best_discount = None
        article_price = self.retail or 0.0  # FIXME: how to handle None prices?
        if not article_price:
            return None
        for skel in SHOP_INSTANCE.get().discount.current_automatically_discounts:
            # TODO: if can apply (article range, lang, ...)
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
                logger.warning("#TODO: this case is tricky")  # #TODO: this case is tricky
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
                price = self.apply_discount(discount, price)
            if price < best_price:  # Is this discount better?
                best_price = price
                best_discounts = permutation

        return best_price, best_discounts

    # @property
    @functools.cached_property
    def vat_rate(self) -> float:
        """Vat rate for the article

        :returns: value as float (0.0 <= value <= 1.0)
        """
        if not (vat := self.article_skel["shop_vat"]):
            return 0.0
        return (vat["dest"]["rate"] or 0.0) / 100

    @property
    def vat_value(self) -> float:
        """Calculate the vat value based on current price and vat rate"""
        try:
            return toolkit.round_decimal(self.vat_rate * self.current, 2)
        except TypeError:  # One value is None
            return 0.0

    def to_dict(self):
        from viur.shop.types import ExtendedCustomJsonEncoder
        return {
            attr_name: getattr(self, attr_name)
            for attr_name, attr_value in vars(self.__class__).items()
            if isinstance(attr_value, (property, functools.cached_property))
        } | utils.json.loads(utils.json.dumps({  # must be JSON serializable for vi renderer
            "cart_discounts": self.cart_discounts,
            "article_discount": self.article_discount,
        }, cls=ExtendedCustomJsonEncoder))

    @staticmethod
    def apply_discount(
        discount_skel: SkeletonInstance,
        article_price: float
    ):
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

    @classmethod
    def get_or_create(cls, src_object):
        """Get a existing cached or create a new Price object for ArticleSkel or CartItemSkel and cache it"""
        # logger.debug(f"Called get_or_create with {src_object = }")
        try:
            cls.cache[src_object["key"]]
            logger.info(f'Price.get_or_create() hit cache for {src_object["key"]}')
            return cls.cache[src_object["key"]]
        except KeyError:
            pass
        obj = Price(src_object)
        cls.cache[src_object["key"]] = obj
        return obj

    @classmethod
    @property
    def cache(cls):
        return current.request_data.get().setdefault("viur.shop", {}).setdefault("price_cache", {})
