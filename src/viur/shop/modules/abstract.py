import typing as t

from viur.core import Module, current, translate
from viur.core.prototypes import List, Tree
from viur.core.prototypes.tree import SkelType
from viur.core.render.abstract import AbstractRenderer
from viur.core.skeleton import SkeletonInstance
from ..globals import SHOP_LOGGER

if t.TYPE_CHECKING:
    from viur.shop import Shop

logger = SHOP_LOGGER.getChild(__name__)


class ShopModuleAbstract(Module):
    """Abstract Class for all viur-shop sub/nested modules.

    The implementations should set `moduleName` as class variable,
    so the final module name for routing it not affected by the name
    of custom classes.
    """

    reference_user_created_skeletons_in_session: bool = False
    """If True, keys of skeletons that the current user has created will be stored in the session."""

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
        # logger.debug(f"{self.__class__.__name__}<ShopModuleAbstract>.__init__({moduleName=}, {modulePath=}, {shop=})")
        self._is_registered = False
        if shop is None:
            raise ValueError("Missing shop argument!")
        if moduleName is None:
            moduleName = getattr(self, "moduleName", self.__class__.__name__.lower())
        if modulePath is None:
            modulePath = f"{shop.modulePath}/{moduleName.lower()}"
        try:
            self.kindName = self.kindName.replace("{{viur_shop_modulename}}", shop.moduleName)
        except AttributeError:
            pass
        super().__init__(moduleName, modulePath, *args, **kwargs)
        self.shop: "Shop" = shop

    def register(self, target: dict, render: AbstractRenderer) -> None:
        """
        Overwritten to avoid loops.
        The modules have an `shop` root/parent reference, but this should
        not again be discovered by :meth:`register`.

        Furthermore, this creates a new renderer instance just for this module
        (with the `parent` reference), which does usually the viur-core in
        :meth:`core.__build_app`. Otherwise, every module would use the same
        shop renderer.
        """
        if self._is_registered:
            return
        self._is_registered = True
        render = type(render)(parent=self)  # Create a new renderer instance for this module
        return super().register(target, render)

    @property
    def session(self) -> dict:
        """Return a own session scope for this module"""
        session = current.session.get()
        if session is None:
            logger.warning(f"Session is None!")
            return None
        session_shop = session.setdefault("shop", {})
        if self.moduleName not in session_shop:
            session_shop[self.moduleName] = {}
            session.markChanged()
        return session_shop[self.moduleName]

    def onAdded(self, *args) -> None:
        skel: SkeletonInstance
        skelType: SkelType
        if isinstance(self, List):
            skel, = args
        elif isinstance(self, Tree):
            skelType, skel = args
        else:
            raise NotImplementedError(type(self))
        super().onAdded(*args)  # noqa: Modules which call onAdded, has this in the prototype
        self.session.setdefault("created_skel_keys", []).append(skel["key"])
        current.session.get().markChanged()
