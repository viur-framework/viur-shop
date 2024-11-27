import typing as t

from viur.core import errors, exposed, utils
from viur.core.skeleton import SkeletonInstance

from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..types.exceptions import IllegalOperationError

logger = SHOP_LOGGER.getChild(__name__)


class Invoice(PaymentProviderAbstract):
    """
    Order is directly RTS, but not paid.

    The customer pays this order in the next x days, independent of shipping.
    But this will not be handled or checked here.
    """

    name: t.Final[str] = "invoice"

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> None:
        # TODO: Standardize this, write in txn
        order_skel["payment"].setdefault("payments", []).append({
            "pp": self.name,
            "creationdate": utils.utcNow().isoformat(),
        })
        order_skel.toDB()
        return None

    def charge(self) -> None:
        # An invoice cannot be charged, The user has to do this on his own
        raise IllegalOperationError("An invoice cannot be charged")

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, t.Any]:
        # An invoice payment state cannot be checked without access to the target bank account
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
