import abc
import typing as t  # noqa

from viur.core.bones import *
from viur.shop.types import *
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


# FIXME: TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
class ArticleAbstractSkel:  # FIXME: (abc.ABC):
    """Abstract skeleton class which the project has to implement for the article skeletons

    All members in this abstract skeleton has to be prefixed with `shop_` to
    avoid name collisions with bones in the project skeleton
    """

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

    @property
    def shop_price_(self) -> Price:
        return Price.get_or_create(self)

    shop_price = RawBone(  # FIXME: JsonBone doesn't work (https://github.com/viur-framework/viur-core/issues/1092)
        descr="price",
        compute=Compute(lambda skel: skel.shop_price_.to_dict(), ComputeInterval(ComputeMethod.Always))
    )
    shop_price.type = JsonBone.type
