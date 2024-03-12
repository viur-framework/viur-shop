import unzer
from unzer.model import PaymentType

from viur.core.skeleton import SkeletonInstance
from .unzer_abstract import UnzerAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerPayPal(UnzerAbstract):
    name = "unzer-paypal"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.PayPal(key=type_id)
