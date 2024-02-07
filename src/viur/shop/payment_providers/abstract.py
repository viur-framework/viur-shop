import abc
import logging
import typing as t

from viur.core.skeleton import SkeletonInstance

logger = logging.getLogger("viur.shop").getChild(__name__)


class PaymentProviderAbstract(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    def can_checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
        return []

    @abc.abstractmethod
    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        ...

    def can_order(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
        return []

    @abc.abstractmethod
    def charge(self):
        ...

    @abc.abstractmethod
    def check_payment_state(self):
        ...

    @abc.abstractmethod
    # @exposed
    def return_hook(self):
        ...

    @abc.abstractmethod
    # @exposed
    def webhook(self):
        ...

    @abc.abstractmethod
    # @exposed
    def get_debug_information(self):
        ...
