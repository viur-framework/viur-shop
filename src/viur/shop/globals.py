import logging
import typing as t
from contextvars import ContextVar

if t.TYPE_CHECKING:
    from .shop import Shop

SHOP_LOGGER: logging.Logger = logging.getLogger("viur.shop")

SHOP_INSTANCE: ContextVar["Shop"] = ContextVar("ShopInstance")
SHOP_INSTANCE_VI: ContextVar["Shop"] = ContextVar("ShopInstanceVi")


class Sentinel:
    def __repr__(self) -> str:
        return "<SENTINEL>"

    def __bool__(self) -> bool:
        return False


SENTINEL: t.Final[Sentinel] = Sentinel()
