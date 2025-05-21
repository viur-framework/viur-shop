from __future__ import annotations

import typing as t

from viur.core import translate

from .data import ClientError
from ..globals import SHOP_LOGGER

if t.TYPE_CHECKING:
    from viur.shop import OrderSkel, SkeletonInstance_T

logger = SHOP_LOGGER.getChild(__name__)


class StatusError(t.TypedDict):
    """
    Represents the result of a validation check, including a success flag and a list of errors.

    Used to indicate whether a certain operation (e.g. checkout or order) is allowed.
    """
    status: bool
    errors: list[ClientError]


class OrderViewResult(t.TypedDict):
    """
    Result structure returned when viewing an order, including the skeleton and validation states.

    Contains the order data as well as flags indicating whether checkout or ordering is currently allowed.
    """
    skel: SkeletonInstance_T[OrderSkel]
    can_checkout: StatusError
    can_order: StatusError


class PaymentProviderResult(t.TypedDict):
    """
    Metadata and availability status for a payment provider.

    Includes translated title/description, an optional image path, and a flag for availability.
    """
    title: translate
    descr: translate
    image_path: str | None
    is_available: bool
