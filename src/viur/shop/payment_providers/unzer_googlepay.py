import typing as t

import unzer
from unzer.model import PaymentType

from viur.core.skeleton import SkeletonInstance
from .unzer_abstract import UnzerAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerGooglepay(UnzerAbstract):
    """
    Unzer Google Pay payment method integration for the ViUR Shop.

    Enables customers to pay Google Pay through the Unzer payment gateway.
    """

    name: t.Final[str] = "unzer-googlepay"

    def __init__(
        self,
        *,
        merchant_id: str | t.Callable[[], str],
        merchant_name: str | t.Callable[[], str],
        allow_credit_cards: bool = True,
        allow_prepaid_cards: bool = True,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self._merchant_id = merchant_id
        self._merchant_name = merchant_name
        self.allow_credit_cards = allow_credit_cards
        self.allow_prepaid_cards = allow_prepaid_cards

    @property
    def merchant_id(self) -> str:
        if callable(self._merchant_id):
            return self._merchant_id()
        return self._merchant_id

    @property
    def merchant_name(self) -> str:
        if callable(self._merchant_name):
            return self._merchant_name()
        return self._merchant_name

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.Googlepay(key=type_id)

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        res = super().get_checkout_start_data(order_skel)
        configuration = unzer.Googlepay(client=self.client).get_configuration()["supports"][0]
        return res | {
            "sandbox": self.sandbox,
            "brands": configuration["brands"],
            "channel": configuration["channel"],
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "allow_credit_cards": self.allow_credit_cards,
            "allow_prepaid_cards": self.allow_prepaid_cards,
        }
