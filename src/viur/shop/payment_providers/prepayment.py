import typing as t

from deprecated.sphinx import deprecated

from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance
from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..skeletons import OrderSkel
from ..types import SkeletonInstance_T
from ..types.exceptions import IllegalOperationError

logger = SHOP_LOGGER.getChild(__name__)


class Prepayment(PaymentProviderAbstract):
    """
    Prepayment method for the ViUR Shop.

    Allows customers to place orders with the agreement to pay in advance.
    The order is marked as ready to ship (RTS) once payment is received.

    The customer pays this order in the next x days, shipping will wait.

    Note:
       Payment receipt verification (The customer pays this order in the next x days,
       shipping will wait) is handled externally and not within this module.
    """

    name: t.Final[str] = "prepayment"

    def checkout(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
    ) -> None:
        order_skel = self._append_payment_to_order_skel(order_skel)
        return None

    def charge(self) -> None:
        # An invoice cannot be charged, The user has to do this on his own
        raise IllegalOperationError("A prepayment cannot be charged")

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, t.Any]:
        # A prepayment payment state cannot be checked without access to the target bank account
        # Use meth:`Order.set_paid` to mark an order by external events as paid.
        raise IllegalOperationError("The invoice payment_state cannot be checked by this PaymentProvider")

    @exposed
    def return_handler(self):
        raise errors.NotImplemented  # TODO: We need a generalized solution for this

    @exposed
    def webhook(self):
        # Use meth:`Order.set_paid` to mark an order by external events as paid.
        raise errors.NotImplemented("An invoice has no webhook")  # This NotImplemented is fully intentional

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented  # TODO


@deprecated(
    reason="Class has been renamed, Use :class:`Prepayment`",
    version="0.1.0.dev24",
    action="always",
)
class PrePayment(Prepayment):
    ...
