import logging

from viur.core import errors, exposed
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
