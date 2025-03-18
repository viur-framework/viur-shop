import abc
import inspect
import typing as t  # noqa

from viur.core import utils
from viur.core.bones import *
from viur.core.skeleton import BaseSkeleton
from viur.shop.types import *
from ..globals import SHOP_INSTANCE, SHOP_LOGGER
from ..types.response import make_json_dumpable

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
        """References a FileSkel"""
        ...

    @property
    @abc.abstractmethod
    def shop_art_no_or_gtin(self) -> StringBone:
        ...

    shop_vat_rate_category = SelectBone(
        values=VatRateCategory,
        translation_key_prefix="viur.shop.vat_rate_category.",
        required=True,
        defaultValue=VatRateCategory.STANDARD,
    )

    @property
    @abc.abstractmethod
    def shop_shipping_config(self) -> RelationalBone:
        """References a ShippingConfigSkel"""
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

    shop_view_url = RawBone(
        visible=False,
        compute=Compute(
            lambda skel: utils.seoUrlToEntry(skel.kindName, skel),
            ComputeInterval(ComputeMethod.Always),
        ),
    )
    """URL to the article page (view)"""

    @property
    def shop_price_(self) -> Price:
        return Price.get_or_create(self)

    shop_price = JsonBone(
        compute=Compute(lambda skel: skel.shop_price_.to_dict(), ComputeInterval(ComputeMethod.Always))
    )

    shop_shipping = JsonBone(
        compute=Compute(
            lambda skel: make_json_dumpable(SHOP_INSTANCE.get().shipping.choose_shipping_skel_for_article(skel)),
            ComputeInterval(ComputeMethod.Always)),
    )
    """Calculated, cheapest shipping for this article"""

    @classmethod
    def setSystemInitialized(cls):
        # logger.debug(f"Call setSystemInitialized({cls=})")
        # Check if all abstract methods are implemented
        for name in dir(cls):
            value = getattr(cls, name, None)
            if getattr(value, "__isabstractmethod__", False):
                raise TypeError(
                    f"Can't initialize abstract class {cls.__name__} with abstract method {name}"
                )
        # Check if all abstract methods are implemented with the correct type
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
