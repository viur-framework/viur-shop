import abc

import logging

logger = logging.getLogger("viur.shop").getChild(__name__)


class PaymentProviderAbstract(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def checkout(self):
        ...

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
