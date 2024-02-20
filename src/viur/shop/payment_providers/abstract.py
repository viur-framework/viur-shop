import abc
import logging
import typing as t

from viur.core import Module
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import SkeletonInstance

from .. import ClientError

if t.TYPE_CHECKING:
    from ..shop import Shop

logger = logging.getLogger("viur.shop").getChild(__name__)


class PaymentProviderAbstract(InstancedModule, Module, abc.ABC):
    shop: "Shop" = None

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Define the name of the payment provider"""
        ...

    def can_checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> list[ClientError]:
        """Check if a checkout process can be started

        An empty list means not error,
        a list with errors rejects the checkout start.
        """
        return []

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
