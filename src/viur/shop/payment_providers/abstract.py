import abc
import typing as t

from viur.core import Module, translate
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import SkeletonInstance
from viur.shop.types.response import T

from viur.shop.skeletons.order import OrderSkel
from ..types import ClientError, SkeletonInstance_T

if t.TYPE_CHECKING:
    from ..shop import Shop

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class PaymentProviderAbstract(InstancedModule, Module, abc.ABC):
    shop: "Shop" = None

    def __init__(
        self,
        *,
        image_path: str | None = None,
        is_available: t.Callable[[SkeletonInstance_T[OrderSkel] | None], bool] | None = None,
    ) -> None:
        super().__init__()
        self.image_path = image_path
        if is_available is not None:
            assert callable(is_available), f"{is_available=} ({type(is_available)})"
            self.is_available = is_available

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Define the internal name of the payment provider"""
        ...

    @property
    def title(self) -> translate:
        """Define the external title of the payment provider"""
        return translate(f"viur.shop.payment_provider.{self.name}", self.name)

    @property
    def description(self) -> translate:
        """Define the description of the payment provider"""
        return translate(f"viur.shop.payment_provider.{self.name}.descr", self.name)

    def is_available(
        self,
        order_skel: SkeletonInstance_T[OrderSkel] | None,
    ) -> bool:
        return True

    def can_checkout(
        self,
        order_skel: SkeletonInstance_T[OrderSkel] | None,
    ) -> list[ClientError]:
        """Check if a checkout process can be started

        An empty list means not error,
        a list with errors rejects the checkout start.
        """
        errs = []
        if not self.is_available:
            errs.append(ClientError("is not available", True))
        return errs

    @abc.abstractmethod
    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        ...

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        return None

    def can_order(
        self,
        order_skel: SkeletonInstance,
    ) -> list[ClientError]:
        return []

    @abc.abstractmethod
    def charge(self):
        ...

    @abc.abstractmethod
    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, t.Any]:
        ...

    @abc.abstractmethod
    # @exposed
    def return_handler(self):
        ...

    @abc.abstractmethod
    # @exposed
    def webhook(self):
        ...

    @abc.abstractmethod
    # @exposed
    def get_debug_information(self):
        ...


PaymentProviderAbstract.html = True
