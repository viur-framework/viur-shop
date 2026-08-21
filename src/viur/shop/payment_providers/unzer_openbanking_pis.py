import typing as t

import unzer
from unzer.model import PaymentType
from viur.core import db, errors, exposed
from viur.core.skeleton import SkeletonInstance

from viur import toolkit
from .unzer_abstract import UnzerAbstract, log_unzer_error
from ..globals import SHOP_LOGGER
from ..services import HOOK_SERVICE, Hook
from ..types import error_handler

logger = SHOP_LOGGER.getChild(__name__)


class UnzerOpenbankingPis(UnzerAbstract):
    """Unzer Direct Bank Transfer (Open Banking PIS) for the ViUR Shop.

    Pay-by-bank based on a payment initiation service: the customer is redirected to
    log into their own online banking and authorizes the transfer there. Available in
    Germany and Austria in EUR, and replaces Sofort.

    The charge is not settled when the customer returns -- the transfer takes one up
    to seven business days to arrive. Until then the order remains unpaid and the
    payment is flagged as pending, see :meth:`return_handler`.
    """

    name: t.Final[str] = "unzer-openbanking_pis"

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        """Build the payment type from the resource the frontend created.

        :param order_skel: OrderSkel holding the payment attempt.
        :return: The direct bank transfer payment type to charge.
        """
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.OpenbankingPis(key=type_id)

    def get_pending_payment_ids(
        self,
        payment: t.Any,
        order_skel: SkeletonInstance,
    ) -> set[str]:
        """Collect the payments whose charge was initiated but has not settled yet.

        Unlike card or wallet payments, a direct bank transfer is not settled when the
        customer returns from the bank: the charge stays ``pending`` until the money
        actually arrives, which takes one up to seven business days. Only then does
        ``amountCharged`` reach the order total and the payment count as paid.

        :param payment: Payment data as returned by :meth:`UnzerAbstract.check_payment_state`,
            either a single payment or a list of them.
        :param order_skel: OrderSkel the payment belongs to.
        :return: Ids of the payments the customer authorized and that await settlement.
        """
        payments = payment if isinstance(payment, list) else [payment]
        return {
            single_payment.paymentId
            for single_payment in payments
            for transaction in (single_payment.transactions or ())
            if transaction.action == "charge"
            and transaction.status == "pending"
            and transaction.amount == order_skel["total"]
        }

    def mark_payments_pending(
        self,
        order_skel: SkeletonInstance,
        payment_ids: set[str],
    ) -> SkeletonInstance:
        """Flag the payments that await settlement on the order.

        The order stays unpaid, so the flag is what tells a shop frontend apart a
        payment that failed from one that was placed successfully and is on its way.

        :param order_skel: OrderSkel to update.
        :param payment_ids: Ids of the payments to flag, see :meth:`get_pending_payment_ids`.
        :return: The written OrderSkel.
        """

        def set_pending(skel: SkeletonInstance) -> None:
            for entry in skel["payment"]["payments"]:
                if entry.get("payment_id") in payment_ids:
                    entry["pending"] = True

        return toolkit.set_status(
            key=order_skel["key"],
            values=set_pending,
            skel=order_skel,
        )

    @exposed
    @log_unzer_error
    @error_handler
    def return_handler(
        self,
        order_key: db.Key,
    ) -> t.Any:
        """Return Endpoint

        Endpoint to which customers are redirected once they have processed a payment on the payment server.

        Overwritten to accept a pending settlement: a transfer the customer just
        authorized is a successful checkout, even though the order stays unpaid until
        the money arrives and the webhook marks it as paid.
        """
        # TODO: drop this override once check_payment_state can report a pending state
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.viewSkel()
        if not order_skel.read(order_key):
            raise errors.NotFound
        is_paid, payment = self.check_payment_state(order_skel)
        if is_paid and order_skel["is_paid"]:
            logger.info(f'Order {order_skel["key"]} already marked as paid. Nothing to do.')
        elif is_paid:
            logger.info(f'Mark order {order_skel["key"]} as paid')
            order_skel = self.shop.order.set_paid(order_skel)
        elif pending_payment_ids := self.get_pending_payment_ids(payment, order_skel):
            logger.info(f'Charge of order {order_skel["key"]} is awaiting settlement')
            order_skel = self.mark_payments_pending(order_skel, pending_payment_ids)
        else:
            return HOOK_SERVICE.dispatch(Hook.PAYMENT_RETURN_HANDLER_ERROR)(order_skel, payment)
        return HOOK_SERVICE.dispatch(Hook.PAYMENT_RETURN_HANDLER_SUCCESS)(order_skel, payment)
