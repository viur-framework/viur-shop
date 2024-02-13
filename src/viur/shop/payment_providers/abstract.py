import abc
import logging
import typing as t

from viur.core import Module, exposed
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import SkeletonInstance

if t.TYPE_CHECKING:
    from ..shop import Shop

logger = logging.getLogger("viur.shop").getChild(__name__)


class PaymentProviderAbstract(InstancedModule, Module, abc.ABC):
    shop: "Shop" = None

    # _module_name = None
    # _module_path = None
    #
    # @property
    # def moduleName(self) -> str:
    #     if self._module_name is not None:
    #         return self._module_name
    #     return f"pp_{self.name}".replace("-", "_")
    #
    # @moduleName.setter
    # def moduleName(self, value: str) -> None:
    #     self._module_name = value
    #
    # @property
    # def modulePath(self) -> str:
    #     if self._module_path is not None:
    #         return self._module_path
    #     return f"{self.shop.modulePath}/{self.moduleName}"
    #
    # @modulePath.setter
    # def modulePath(self, value: str) -> None:
    #     self._module_path = value

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

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        return None

    def can_order(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
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
