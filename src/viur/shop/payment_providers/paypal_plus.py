import logging
import typing as t

from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance
from . import PaymentProviderAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class PayPalPlus(PaymentProviderAbstract):
    name = "paypal_plus"

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
