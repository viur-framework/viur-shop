import abc
import logging
import typing as t

from viur.core.bones import *
from viur.shop import DiscountType

if t.TYPE_CHECKING:
    from viur.core.skeleton import SkeletonInstance

logger = logging.getLogger("viur.shop").getChild(__name__)


# FIXME: TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
class ArticleAbstractSkel:  # FIXME: (abc.ABC):

    @property
    @abc.abstractmethod
    def shop_name(self):
        """Name of the article in the shop"""
        ...

    @property
    @abc.abstractmethod
    def shop_description(self):
        ...

    @property
    @abc.abstractmethod
    def shop_price_retail(self):
        ...

    @property
    @abc.abstractmethod
    def shop_price_recommended(self):
        ...

    @property
    @abc.abstractmethod
    def shop_availability(self):
        ...

    @property
    @abc.abstractmethod
    def shop_listed(self) -> bool:
        ...

    @property
    @abc.abstractmethod
    def shop_image(self):
        ...

    @property
    @abc.abstractmethod
    def shop_art_no_or_gtin(self):
        ...

    @property
    @abc.abstractmethod
    def shop_vat(self):
        ...

    @property
    @abc.abstractmethod
    def shop_shipping(self):
        ...

    @property
    @abc.abstractmethod
    def shop_is_weee(self) -> bool:
        """Waste Electrical and Electronic Equipment Directive (WEEE Directive)"""
        ...

    @property
    @abc.abstractmethod
    def shop_is_low_price(self) -> bool:
        """shop_price_retail != shop_price_recommended"""
        ...

    # --- Calculating helpers -------------------------------------------------

    @property
    def shop_current_discount(self) -> None | tuple[float, "SkeletonInstance"]:
        """Best permanent discount campaign for article"""
        from viur.shop.shop import SHOP_INSTANCE
        best_discount = None
        article_price = self["shop_price_retail"] or 0  # FIXME: how to handle None prices?
        if not article_price:
            return None
        for skel in SHOP_INSTANCE.get().discount.current_automatically_discounts:
            # TODO: if can apply (article range, lang, ...)
            if skel["discount_type"] == DiscountType.ABSOLUTE:
                price = article_price - skel["absolute"]
            elif skel["discount_type"] == DiscountType.PERCENTAGE:
                price = article_price - (
                    article_price * skel["percentage"] / 100
                )
            else:
                logger.info(f"NotSupported discount: {skel=}")
                continue
            if best_discount is None or price < best_discount[1]:
                best_discount = price, skel
        return best_discount

    @property
    def shop_current_price(self):
        """Price with or without discount"""
        if (discount := self.shop_current_discount) is not None:
            price, skel = discount
            logger.debug(f'Applied {discount=} --> {price}')
            return price
        logger.debug(f'Applied no discount --> keep {self["shop_price_retail"]}')
        return self["shop_price_retail"] or 0  # FIXME: how to handle None prices?

    shop_price_current = NumericBone(
        descr="shop_price_current",
        compute=Compute(lambda skel: skel.shop_current_price, ComputeInterval(ComputeMethod.Always)),
        precision=2,
    )
