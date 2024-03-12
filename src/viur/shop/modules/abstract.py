import typing as t

from viur.core import Module, current, translate
from ..globals import SHOP_LOGGER

if t.TYPE_CHECKING:
    from viur.shop import Shop

logger = SHOP_LOGGER.getChild(__name__)


class ShopModuleAbstract(Module):

    def adminInfo(self) -> dict:
        return {
            "name": translate(f"viur.shop.module.{self.moduleName.lower()}"),
            "moduleGroup": self.shop.admin_info_module_group,
        }

    def __init__(
        self,
        moduleName: str = None,
        modulePath: str = None,
        shop: "Shop" = None,
        *args, **kwargs
    ):
        # logger.debug(f"{self.__class__.__name__}<ShopModuleAbstract>.__init__()")
        if shop is None:
            raise ValueError("Missing shop argument!")
        if moduleName is None:
            moduleName = self.__class__.__name__.lower()
        if modulePath is None:
            modulePath = f"{shop.modulePath}/{moduleName.lower()}"
        super().__init__(moduleName, modulePath, *args, **kwargs)
        self.shop: "Shop" = shop

    @property
    def session(self) -> dict:
        """Return a own session scope for this module"""
        session = current.session.get()
        if session is None:
            logger.warning(f"Session is None!")
            return None
        # TODO: custom session name
        # TODO: Implement .setdefault() in viur.core.Session
        if "shop" not in session:
            session["shop"] = {}
        session_shop = session["shop"]
        if self.moduleName not in session_shop:
            session_shop[self.moduleName] = {}
            session.markChanged()
        return session_shop[self.moduleName]
