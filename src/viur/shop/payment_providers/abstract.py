import abc
import functools
import uuid

from viur.core import CallDeferred, Module, current, db, translate, utils
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import SkeletonInstance

from viur import toolkit
from viur.shop.skeletons.order import OrderSkel
from ..types import *

if t.TYPE_CHECKING:
    from ..shop import Shop

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class PaymentProviderAbstract(InstancedModule, Module, abc.ABC):
    """
    Abstract base class for all payment providers in the ViUR Shop.

    Provides a standardized interface for implementing different payment methods,
    including methods for checkout, charging, and handling payment states.

    Subclasses must implement the required methods to integrate specific payment providers.
    """

    shop: "Shop" = None
    """Reference to the main :class:`Shop` instance."""

    def __init__(
        self,
        *,
        image_path: str | None = None,
        is_available: t.Callable[[t.Self, SkeletonInstance_T[OrderSkel] | None], bool] | None = None,
    ) -> None:
        super().__init__()
        self.image_path = image_path
        if is_available is not None:
            assert callable(is_available), f"{is_available=} ({type(is_available)})"
            self.is_available = functools.partial(is_available, self)  # type: ignore[assignment]

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
        self: t.Self,
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
        if not self.is_available(order_skel):
            errs.append(ClientError(f"PaymentProvider {self.name} is not available", True))
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
        """
        Check the payment state from the PaymentProvider API/service

        Access :attr:`OrderSkel.is_paid` to get the payment state of an order.
        """
        ...

    @CallDeferred
    # @log_unzer_error
    def check_payment_deferred(self, order_key: db.Key) -> None:
        """Check the status for a payment deferred"""
        logger.debug(f"Checking payment for {order_key=!r} deferred")
        order_skel = self.shop.order.skel().read(order_key)
        logger.debug(f"Checking payment for {order_skel=!r} deferred")
        # TODO: duplicate check / code?
        is_paid, payment = self.check_payment_state(order_skel)
        if is_paid and order_skel["is_paid"]:
            logger.info(f'Order {order_skel["key"]!r} already marked as paid. Nothing to do.')
        elif is_paid:
            logger.info(f'Mark order {order_skel["key"]!r} as paid')
            self.shop.order.set_paid(order_skel)
        else:
            logger.info(f'Order {order_skel["key"]!r} is not paid')

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

    def _append_payment_to_order_skel(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
        payment: PaymentTransactionSpecific | None = None,
    ) -> SkeletonInstance_T[OrderSkel]:
        """Append payment data to an order

        Append payment_provider name and creationdate by default.
        Write safely in a transaction.
        """

        def set_payment(skel: SkeletonInstance):
            if not skel["payment"]:
                skel["payment"] = {}
            skel["payment"].setdefault("payments", []).append(
                {
                    "payment_provider": self.name,
                    "creationdate": utils.utcNow().isoformat(),
                    "uuid": str(uuid.uuid4()),
                    "client_ip": current.request.get().request.client_addr,
                    "user_agent": current.request.get().request.user_agent,
                }
                | (payment or {})  # type: PaymentTransaction
            )

        order_skel = toolkit.set_status(
            key=order_skel["key"],
            values=set_payment,
            skel=order_skel,
        )
        return order_skel

    def serialize_for_api(
        self,
        order_skel: SkeletonInstance_T[OrderSkel] | None,
    ) -> PaymentProviderResult:
        """Serialize this Payment Provider for the API

        Used by :meth:`Order.get_payment_providers` and :meth:`Order.payment_providers_list`
        Can be subclasses to expose more information via API.
        """
        return PaymentProviderResult(
            title=self.title,
            descr=self.description,
            image_path=self.image_path,
            is_available=self.is_available(order_skel),
        )


PaymentProviderAbstract.html = True
