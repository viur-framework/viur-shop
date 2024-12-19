from __future__ import annotations

import typing as t

from viur.core import translate

from .data import ClientError
from ..globals import SHOP_LOGGER

if t.TYPE_CHECKING:
    from viur.shop import OrderSkel, SkeletonInstance_T

logger = SHOP_LOGGER.getChild(__name__)


class StatusError(t.TypedDict):
    status: bool
    errors: list[ClientError]


class OrderViewResult(t.TypedDict):
    skel: SkeletonInstance_T[OrderSkel]
    can_checkout: StatusError
    can_order: StatusError


class PaymentProviderResult(t.TypedDict):
    title: translate
    descr: translate
    image_path: str | None
    is_available: bool
