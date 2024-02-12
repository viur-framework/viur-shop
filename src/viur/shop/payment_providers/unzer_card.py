import logging
import typing as t

import unzer
from unzer.model.payment import PaymentState
from viur.core import current, db, errors, exposed
from viur.core.skeleton import SkeletonInstance

from .unzer_abstract import UnzerAbstract
from .. import exceptions as e

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

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, unzer.PaymentGetResponse]:
        payment_id = order_skel["payment"]["payments"][-1]["payment_id"]
        logger.debug(f"{payment_id = }")
        payment = self.client.getPayment(payment_id)
        payment_id = str(order_skel["key"].id_or_name)
        logger.debug(f"{payment_id = }")
        payment = self.client.getPayment(payment_id)
        logger.debug(f"{payment = }")

        if str(payment.invoiceId) != str(order_skel["order_uid"]):
            raise e.InvalidStateError(f'{payment.invoiceId} != {order_skel["order_uid"]}')

        if payment.state == PaymentState.COMPLETED and payment.amountCharged == order_skel["total"]:
            return True, payment
        return False, payment

    @exposed
    def return_handler(
        self,
        order_key: db.Key,
    ) -> t.Any:
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.viewSkel()
        if not order_skel.fromDB(order_key):
            raise errors.NotFound
        is_paid, payment = self.check_payment_state(order_skel)
        charges = payment.getChargedTransactions()
        logger.debug(f"{charges = }")
        if is_paid and order_skel["is_paid"]:
            logger.info(f'Order {order_skel["key"]} already marked as paid. Nothing to do.')
        elif is_paid:
            logger.info(f'Mark order {order_skel["key"]} as paid')
            order_skel["is_paid"] = True  # TODO: transaction
            order_skel.toDB()
        else:
            raise errors.NotImplemented("Order not paid")
        return "OKAY, paid"

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
