import typing as t

from viur.core import Module

if t.TYPE_CHECKING:
    from viur.shop import Shop

import logging

logger = logging.getLogger("viur.shop").getChild(__name__)


class ShopModuleAbstract(Module):

    def __init__(
        self,
        moduleName: str = None,
        modulePath: str = None,
        shop: "Shop" = None,
        *args, **kwargs
    ):
        if shop is None:
            raise ValueError("Missing shop argument!")
        if moduleName is None:
            moduleName = self.__class__.__name__
        if modulePath is None:
            modulePath = f"{shop.modulePath}/{moduleName.lower()}"
        super().__init__(moduleName, modulePath, *args, **kwargs)
        self.shop: "Shop" = shop
