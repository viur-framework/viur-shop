import logging
import typing as t  # noqa

from viur.core import current
from viur.core.skeleton import SkeletonInstance
from viur.shop import DiscountType

logger = logging.getLogger("viur.shop").getChild(__name__)
logger.debug = logger.critical


class Price:
    cart_discounts: list[SkeletonInstance] = []
    article_discount: SkeletonInstance = None

    is_in_cart = None
    article_skel = None
    cart_leaf = None

    def __init__(self, src_object):
        super().__init__()
        # logger.debug(f"Creating new price object based on {src_object=}")
        from .shop import SHOP_INSTANCE

        shop = SHOP_INSTANCE.get()
        if isinstance(src_object, SkeletonInstance) and issubclass(src_object.skeletonCls, shop.cart.leafSkelCls):
            self.is_in_cart = True
            self.cart_leaf = src_object
            self.article_skel = src_object.article_skel_full
            self.cart_discounts = shop.cart.get_discount_for_leaf(src_object)
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
        return self.retail - self.current

    @property
    def saved_percentage(self) -> float:
        return self.current / self.saved

    @property
    # @functools.cached_property
    def current(self) -> float:
        if (not self.is_in_cart or not self.cart_discounts) and self.article_discount:
            # only the article_discount is applicable
            return self.apply_discount(self.article_discount, self.retail)
        if self.is_in_cart and self.cart_discounts:
            # TODO: if self.article_discount:
            price = self.retail
            for discount in self.cart_discounts:  # TODO: check combinable, best-choice
                price = self.apply_discount(discount, price)
            return price
        return self.retail

    def shop_current_discount(self, skel) -> None | tuple[float, "SkeletonInstance"]:
        """Best permanent discount campaign for article"""
        from viur.shop.shop import SHOP_INSTANCE
        best_discount = None
        article_price = self.retail or 0.0  # FIXME: how to handle None prices?
        if not article_price:
            return None
        for skel in SHOP_INSTANCE.get().discount.current_automatically_discounts:
            # TODO: if can apply (article range, lang, ...)
            price = self.apply_discount(skel, article_price)
            if best_discount is None or price < best_discount[1]:
                best_discount = price, skel
        return best_discount

    def choose_best_discount_set(self):
        ...

    @property
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
        return self.vat_rate * self.current

    def to_dict(self):
        _current = self.current

        return {
            attr_name: getattr(self, attr_name)
            for attr_name, attr_value in vars(self.__class__).items()
            if isinstance(attr_value, property)
        }

        return {
            "retail": self.retail,
            "recommended": self.recommended,
            "current": _current,
            "saved": self.saved,
            "saved_percentage": self.saved_percentage,
            "cart_discounts": self.cart_discounts,
            "article_discount": self.article_discount,
        }

    @staticmethod
    def apply_discount(
        discount_skel: SkeletonInstance,
        article_price: float
    ):
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
        # logger.debug(f"Called get_or_create with {src_object = }")
        try:
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
