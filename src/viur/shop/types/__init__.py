import typing as t

from viur.core.skeleton import Skeleton as _Skeleton, SkeletonInstance as _SkeletonInstance

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
    IllegalOperationError,
    InvalidArgumentException,
    InvalidKeyException,
    InvalidStateError,
    MissingArgumentsException,
    TooManyArgumentsException,
    ViURShopException,
    ViURShopHttpException,
)
from .price import Price  # noqa
from .response import ExtendedCustomJsonEncoder, JsonResponse  # noqa
from .results import (OrderViewResult, PaymentProviderResult, StatusError)  # noqa
