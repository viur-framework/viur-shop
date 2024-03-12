import abc
import enum
import typing as t

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Hook(enum.IntEnum):
    ORDER_ASSIGN_UID = enum.auto()


class Customization(abc.ABC):
    @property
    @abc.abstractmethod
    def kind(self) -> Hook:
        ...

    @abc.abstractmethod
    def __call__(self, *args, **kwargs) -> t.Any:
        ...

    def __repr__(self) -> str:
        return f"<Customization {self.__class__.__name__} for {self.kind.name}>"

    @classmethod
    def from_method(cls, func: t.Callable, kind: Hook) -> t.Self:
        return type(
            f"{kind}_{func.__name__}{cls.__name__}",
            (cls,),
            {"__call__": staticmethod(func), "kind": kind}
        )()


class HookService:
    customizations: t.Final[list[Customization]] = []

    def register(self, customization: Customization):
        if not isinstance(customization, Customization):
            raise TypeError(f"customization must be of type Customization")
        # TODO: What happens on existing hooks for the same kind?
        HookService.customizations.append(customization)
        return customization

    def unregister(self, customization: Customization):
        HookService.customizations.remove(customization)

    def dispatch(self, kind: Customization, default: t.Callable = None):
        for customization in HookService.customizations:
            if kind is customization.kind:  # TODO: add by_kind map
                logger.debug(f"found {customization=}")
                return customization
        logger.debug(f"found no customization")
        if default is None:
            raise ValueError(f"No customization found for {kind}")
        logger.debug(f"use default customization {default=}")
        return default


HOOK_SERVICE = HookService()
