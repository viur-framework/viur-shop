import logging
import typing as t
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from .shop import Shop

SHOP_LOGGER: logging.Logger = logging.getLogger("viur.shop")

SHOP_INSTANCE: ContextVar["Shop"] = ContextVar("ShopInstance")
SHOP_INSTANCE_VI: ContextVar["Shop"] = ContextVar("ShopInstanceVi")

SENTINEL: t.Final[object] = object()
