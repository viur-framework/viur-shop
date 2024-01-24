import logging

from viur.core import errors, exposed
from . import PaymentProviderAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class PayPalPlus(PaymentProviderAbstract):
    name = "paypal_plus"

    def checkout(self):
        raise errors.NotImplemented()

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(self):
        raise errors.NotImplemented()

    @exposed
    def return_hook(self):
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
