import typing as t

from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance

from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class PayPalPlus(PaymentProviderAbstract):
    """
    PayPal Plus integration for the ViUR Shop.

    Supports multiple payment methods through PayPal Plus, including PayPal, credit card, and more.
    Handles the checkout process, payment state checks, and webhook handling for payment updates.
    """

    name: t.Final[str] = "paypal_plus"

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        raise errors.NotImplemented()

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(self):
        raise errors.NotImplemented()

    @exposed
    def return_handler(self):
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
