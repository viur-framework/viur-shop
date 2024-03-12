import unzer
from unzer.model import PaymentType

from viur.core.skeleton import SkeletonInstance
from .unzer_abstract import UnzerAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerCard(UnzerAbstract):
    name = "unzer-card"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.Card(key=type_id)
