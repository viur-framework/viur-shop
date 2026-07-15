import typing as t

import unzer
from unzer.model import PaymentType
from viur.core.skeleton import SkeletonInstance

from .unzer_abstract import UnzerAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerKlarna(UnzerAbstract):
    """
    Unzer Klarna payment method integration for the ViUR Shop.

    Enables customers to pay using Klarna through the Unzer payment gateway.
    """

    name: t.Final[str] = "unzer-klarna"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.Klarna(key=type_id)
