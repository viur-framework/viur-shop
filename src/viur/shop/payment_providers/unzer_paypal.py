import logging
import typing as t

import unzer
from unzer.model import PaymentType
from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance

from .unzer_abstract import UnzerAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class UnzerPayPal(UnzerAbstract):
    name = "unzer-paypal"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.PayPal(key=type_id)

    def charge(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
