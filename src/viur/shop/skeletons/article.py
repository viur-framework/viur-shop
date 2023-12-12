import abc

import logging

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
