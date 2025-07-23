import logging
import typing as t

from .types_global import GlobalVar, Sentinel

if t.TYPE_CHECKING:
    from .shop import Shop

SHOP_LOGGER: logging.Logger = logging.getLogger("viur.shop")
"""viur-shop base logger instance"""

SHOP_INSTANCE: GlobalVar["Shop"] = GlobalVar("ShopInstance")
"""The shop instance bound to the default html renderer"""

SHOP_INSTANCE_VI: GlobalVar["Shop"] = GlobalVar("ShopInstanceVi")
"""The shop instance bound to the vi renderer"""

SENTINEL: t.Final[Sentinel] = Sentinel()
"""Unique sentinel object used to detect if a value was explicitly set or not"""

DEBUG_DISCOUNTS: GlobalVar[bool] = GlobalVar("DEBUG_DISCOUNTS", default=False)
"""Print detailed discount evaluation for debugging"""
