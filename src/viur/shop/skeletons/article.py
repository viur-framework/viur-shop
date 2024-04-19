import abc
import inspect
import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import BaseSkeleton
from viur.shop.types import *

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ArticleAbstractSkel(BaseSkeleton):
    """Abstract skeleton class which the project has to implement for the article skeletons

    All members in this abstract skeleton has to be prefixed with `shop_` to
    avoid name collisions with bones in the project skeleton
    """

    @property
    @abc.abstractmethod
    def shop_name(self) -> StringBone | TextBone:
        """Name of the article in the shop"""
        ...

    @property
    @abc.abstractmethod
    def shop_description(self) -> TextBone:
        ...

    @property
    @abc.abstractmethod
    def shop_price_retail(self) -> NumericBone:
        ...

    @property
    @abc.abstractmethod
    def shop_price_recommended(self) -> NumericBone:
        ...

    @property
    @abc.abstractmethod
    def shop_availability(self) -> SelectBone:
        ...

    @property
    @abc.abstractmethod
    def shop_listed(self) -> BooleanBone:
        ...

    @property
    @abc.abstractmethod
    def shop_image(self) -> FileBone:
        ...

    @property
    @abc.abstractmethod
    def shop_art_no_or_gtin(self) -> StringBone:
        ...

    @property
    @abc.abstractmethod
    def shop_vat(self) -> RelationalBone:
        ...

    @property
    @abc.abstractmethod
    def shop_shipping(self) -> RelationalBone:
        ...

    @property
    @abc.abstractmethod
    def shop_is_weee(self) -> BooleanBone:
        """Waste Electrical and Electronic Equipment Directive (WEEE Directive)"""
        ...

    @property
    @abc.abstractmethod
    def shop_is_low_price(self) -> BooleanBone:
        """shop_price_retail != shop_price_recommended"""
        ...

    @property
    def shop_price_(self) -> Price:
        return Price.get_or_create(self)

    shop_price = RawBone(  # FIXME: JsonBone doesn't work (https://github.com/viur-framework/viur-core/issues/1092)
        compute=Compute(lambda skel: skel.shop_price_.to_dict(), ComputeInterval(ComputeMethod.Always))
    )
    shop_price.type = JsonBone.type

    @classmethod
    def setSystemInitialized(cls):
        logger.debug(f"Call setSystemInitialized({cls=})")
        # Check if all abstract methods are implemented
        for name in dir(cls):
            value = getattr(cls, name, None)
            if getattr(value, "__isabstractmethod__", False):
                raise TypeError(
                    f"Can't initialize abstract class {cls.__name__} with abstract method {name}"
                )
        # Check if all abstract methods are implemented with th correct type
        for name in dir(ArticleAbstractSkel):
            value = getattr(ArticleAbstractSkel, name, None)
            if getattr(value, "__isabstractmethod__", False) and isinstance(value, property):
                annotations = inspect.get_annotations(getattr(ArticleAbstractSkel, name).fget)
                if "return" not in annotations:
                    raise InvalidStateError(
                        f"Dear viur-shop Developer, please add the return type hint to the abstract property {name}!"
                    )
                if not isinstance(value := getattr(cls, name), annotations["return"]):
                    raise TypeError(
                        f'Can\'t initialize class {cls.__name__}: '
                        f'bone {name} must be of type {annotations["return"]} not {type(value)}'
                    )
        super().setSystemInitialized()
