import logging
import typing as t

import unzer

from viur.core import current, errors, exposed
from viur.core.skeleton import SkeletonInstance
from .unzer_abstract import UnzerAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class UnzerCard(UnzerAbstract):
    name = "unzer-card"

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        customer = self.customer_from_order_skel(order_skel)
        logger.debug(f"{customer = }")

        customer = self.client.createOrUpdateCustomer(customer)
        logger.debug(f"{customer = } [RESPONSE]")

        host = current.request.get().request.host_url
        return_url = f'{host}/{self.modulePath}/return_handler?order_key={order_skel["key"].to_legacy_urlsafe().decode("ASCII")}'
        unzer_session = current.session.get()["unzer"] = {
            "customer_id": customer.key,
        }
        type_id = order_skel["payment"]["payments"][-1]["type_id"]

        payment = self.client.charge(
            unzer.PaymentRequest(
                unzer.Card(key=type_id),
                amount=order_skel["total"],
                returnUrl=return_url,
                card3ds=True,
                customerId=customer.key,
                orderId=order_skel["key"].id_or_name,
                invoiceId=order_skel["order_uid"],
            )
        )
        logger.debug(f"{payment=} [charge response]")
        unzer_session["paymentId"] = payment.paymentId
        unzer_session["redirectUrl"] = payment.redirectUrl

        logger.debug(f"{unzer_session = }")
        current.session.get().markChanged()

        # TODO: write in transaction
        order_skel["payment"]["payments"][-1]["payment_id"] = payment.paymentId
        order_skel.toDB()

        return unzer_session

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(self):
        raise errors.NotImplemented()

    @exposed
    def return_handler(self):
        # TODO: check payment
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
