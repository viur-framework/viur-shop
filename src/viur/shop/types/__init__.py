import typing as t

from viur.core.skeleton import Skeleton as _Skeleton, SkeletonInstance as _SkeletonInstance
from .data import ClientError, Supplier  # noqa
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
    OrderState,
    QuantityMode,
    QuantityModeType,
    Salutation,
)
from .exceptions import (  # noqa
    DispatchError,
    InvalidArgumentException,
    InvalidKeyException,
    InvalidStateError,
    ViURShopException,
    ViURShopHttpException,
)
from .price import Price  # noqa
from .response import ExtendedCustomJsonEncoder, JsonResponse  # noqa

SkeletonCls_co = t.TypeVar("SkeletonCls_co", bound=t.Type[_Skeleton], covariant=True)


class SkeletonInstance_T(_SkeletonInstance, t.Generic[SkeletonCls_co]):
    """This types trys to say to which SkeletonCls a SkeletonInstance belongs

    or in other words, it does what the viur-core failed to do.
    """
    ...


del _Skeleton, _SkeletonInstance
