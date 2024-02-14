import logging

import unzer
from unzer.model import PaymentType
from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance

from .unzer_abstract import UnzerAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class UnzerCard(UnzerAbstract):
    name = "unzer-card"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.Card(key=type_id)

    def charge(self):
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
