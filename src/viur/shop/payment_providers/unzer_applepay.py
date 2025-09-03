import typing as t

import unzer
from unzer.model import PaymentType

from viur.core.skeleton import SkeletonInstance
from .unzer_abstract import UnzerAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerApplepay(UnzerAbstract):
    """
    Unzer Apple Pay payment method integration for the ViUR Shop.

    Enables customers to pay Apple Pay through the Unzer payment gateway.
    """

    name: t.Final[str] = "unzer-applepay"

    def __init__(
        self,
        *,
        merchant_name: str | t.Callable[[], str],
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self._merchant_name = merchant_name

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
        return unzer.Applepay(key=type_id)

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        res = super().get_checkout_start_data(order_skel)
        configuration = unzer.Applepay(client=self.client).get_configuration()["supports"][0]
        return res | {
            "sandbox": self.sandbox,
            "brands": configuration["brands"],
            "channel": configuration["channel"],
            "merchant_name": self.merchant_name,
        }
