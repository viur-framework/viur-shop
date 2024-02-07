import logging
import typing as t

from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance
from . import PaymentProviderAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class UnzerAbstract(PaymentProviderAbstract):

    def __init__(
        self,
        private_key: str,
        public_key: str,
        sandbox: bool = False,
        language: str = "en",
    ):
        super().__init__()
        self.private_key = private_key
        self.public_key = public_key
        self.sandbox = sandbox
        self.language = language
        self.client = ...

    def can_checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
        errs = []
        if not order_skel["billing_address"]:
            errs.append("billing_address is missing")
        return errs

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        raise errors.NotImplemented()

    def can_order(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
        # TODO: if payment is prepared ...
        return []

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
