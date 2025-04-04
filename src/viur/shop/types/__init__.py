import typing as t

from viur.core.skeleton import Skeleton as _Skeleton, SkeletonInstance as _SkeletonInstance
from viur.core import i18n

SkeletonCls_co = t.TypeVar("SkeletonCls_co", bound=t.Type[_Skeleton], covariant=True)


class SkeletonInstance_T(_SkeletonInstance, t.Generic[SkeletonCls_co]):
    """This types trys to say to which SkeletonCls a SkeletonInstance belongs

    or in other words, it does what the viur-core failed to do.
    """
    ...


del _Skeleton, _SkeletonInstance

from .data import ClientError, Supplier  # noqa
from .dc_scope import (  # noqa
    DiscountConditionScope,
    ConditionValidator,
    DiscountValidator,
)
from .enums import (  # noqa
    AddressType,
    ApplicationDomain,
    ArticleAvailability,
    CartType,
    CodeType,
    ConditionOperator,
    CustomerGroup,
    CustomerType,
    DiscountType,
    DiscountValidationContext,
    OrderState,
    QuantityMode,
    Salutation,
    ShippingStatus,
    VatRateCategory,
)
from .exceptions import (  # noqa
    ConfigurationError,
    DispatchError,
    InvalidArgumentException,
    InvalidKeyException,
    InvalidStateError,
    IllegalOperationError,
    ViURShopException,
    ViURShopHttpException,
)
from .price import Price  # noqa
from .response import ExtendedCustomJsonEncoder, JsonResponse  # noqa
from .results import (OrderViewResult, PaymentProviderResult, StatusError)  # noqa


class BetterTranslate(i18n.translate):
    """Extent :class:`i18n.translate` with ``default_variables``.

    Should be part of standard: https://github.com/viur-framework/viur-core/issues/1379
    """

    def __init__(self, *args, default_variables: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_variables = default_variables or {}

    def __str__(self):
        return self.substitute_vars(super().__str__(), **self.default_variables)

    def translate(self, **kwargs) -> str:
        return self.substitute_vars(str(self), **(self.default_variables | kwargs))
