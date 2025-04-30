"""Customization / hook service

Register own implementations (:class:`Customization`) to influence
a specific behavior (:class:`Hook`) of the viur-shop.

Unlike events, which are just a trigger, hooks can (and usually should)
modify objects and return something.
"""

import abc
import enum
import typing as t

from viur.shop.types.exceptions import DispatchError
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Hook(enum.IntEnum):
    """The hook'able events / actions."""

    ORDER_ASSIGN_UID = enum.auto()
    """
    Hook that assign a order id on a OrderSkel
    type: (order_skel: SkeletonInstance_T[OrderSkel]) -> SkeletonInstance_T[OrderSkel]
    """

    CURRENT_COUNTRY = enum.auto()
    """Provide the country of a global site context
    type: (context: t.Literal["cart", "article", "vat_rate"]) -> str
    """

    ORDER_ADD_ADDITION = enum.auto()
    """Do some additional modifications on the OrderSkel on order_add action.
    Called in :meth:`viur.shop.modules.order.Order.order_add` before saving with :meth:`Skeleton.write`.
    type: (order_skel: SkeletonInstance_T[OrderSkel]) -> SkeletonInstance_T[OrderSkel]
    """

    ORDER_UPDATE_ADDITION = enum.auto()
    """Do some additional modifications on the OrderSkel on order_update action.
    Called in :meth:`viur.shop.modules.order.Order.order_update` before saving with :meth:`Skeleton.write`.
    type: (order_skel: SkeletonInstance_T[OrderSkel]) -> SkeletonInstance_T[OrderSkel]
    """

    ORDER_CHECKOUT_START_ADDITION = enum.auto()
    """Do some additional modifications on the OrderSkel on checkout_start action.
    Called in :meth:`viur.shop.modules.order.Order.checkout_start` before saving with :meth:`Skeleton.write`.
    type: (order_skel: SkeletonInstance_T[OrderSkel]) -> SkeletonInstance_T[OrderSkel]
    """

    PAYMENT_RETURN_HANDLER_SUCCESS = enum.auto()
    """
    The action that is executed after the customer has returned
    from the payment provider and the payment has been successful.
    This can be, for example, a rendered template or a redirect to another page.
    type: (order_skel: SkeletonInstance_T[OrderSkel], payment_data: t.Any) -> t.Any
    """

    PAYMENT_RETURN_HANDLER_ERROR = enum.auto()
    """
    The action that is executed after the customer has returned
    from the payment provider and the payment has failed.
    This can be, for example, a rendered template or a redirect to another page.
    type: (order_skel: SkeletonInstance_T[OrderSkel], payment_data: t.Any) -> t.Any
    """


class Customization(abc.ABC):
    """Abstract base class for own implementations."""

    @property
    @abc.abstractmethod
    def kind(self) -> Hook:
        """The action this implementation is for"""
        ...

    @abc.abstractmethod
    def __call__(self, *args, **kwargs) -> t.Any:
        """The main logic of this implementation"""
        ...

    def __repr__(self) -> str:
        return f"<Customization {self.__class__.__name__} for {self.kind.name}>"

    @classmethod
    def from_method(cls, func: t.Callable, kind: Hook) -> t.Self:
        """Just a handy variant to define an implementation without a class definition"""
        return type(
            f"{kind}_{func.__name__}{cls.__name__}",
            (cls,),
            {"__call__": staticmethod(func), "kind": kind}
        )()


class HookService:
    """

    Note: Methods should be called only with positional arguments. Or keyword-only if really necessary.
    """

    customizations: t.Final[list[Customization]] = []

    def register(self, customization: Customization | t.Type[Customization]) -> Customization:
        """Register a customization with this service

        Can be used as class decorator too

        .. code-block:: python

            @HOOK_SERVICE.register
            class MyImplementation(Customization):
                kind = Hook.ORDER_ASSIGN_UID

                def __call__(self, *args, **kwargs) -> t.Any:
                    ...
        """
        if not isinstance(customization, Customization):
            if issubclass(customization, Customization):
                customization = customization()
            else:
                raise TypeError(f"customization must be of type Customization")
        # TODO: What happens on existing hooks for the same kind?
        HookService.customizations.append(customization)
        return customization

    def unregister(self, customization: Customization):
        HookService.customizations.remove(customization)

    def dispatch(self, kind: Hook, default: t.Callable = None) -> t.Callable:
        """Choose the matching registered customization for this kind"""
        for customization in HookService.customizations:
            if kind is customization.kind:  # TODO: add by_kind map
                logger.debug(f"found {customization=}")
                return customization
        logger.debug(f"found no customization")
        if default is None:
            raise DispatchError(f"No customization found for {kind!r}", kind)
        logger.debug(f"use default customization {default=}")
        return default


HOOK_SERVICE = HookService()
