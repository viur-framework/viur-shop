import typing as t

import unzer
from unzer import PaymentResponse
from unzer.model import PaymentType
from unzer.model.payment import PaymentState

from viur import toolkit
from viur.core import current
from viur.core.skeleton import SkeletonInstance
from .unzer_abstract import UnzerAbstract, log_unzer_error
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerKlarna(UnzerAbstract):
    """
    Unzer Klarna payment method integration for the ViUR Shop.

    Enables customers to pay using Klarna through the Unzer payment gateway.

    Klarna is a Buy Now Pay Later (BNPL) method and cannot be charged
    directly: the payment must be authorized first (together with a basket
    resource) and charged later (e.g. on shipment).
    See https://docs.unzer.com/payment-methods/klarna/.
    """

    name: t.Final[str] = "unzer-klarna"

    def __init__(
        self,
        *args: t.Any,
        charge_directly: bool = True,
        **kwargs: t.Any,
    ) -> None:
        """
        :param charge_directly: If ``True``, capture (charge) the payment as
            soon as the customer returns from the Klarna redirect. If
            ``False``, only authorize and defer the capture (e.g. to shipment).

            Note: Klarna can never be charged during ``checkout`` itself — the
            customer must approve the payment at the redirect first, so the
            capture always happens in the return flow at the earliest.
        """
        super().__init__(*args, **kwargs)
        self.charge_directly = charge_directly

    # --- Payment flow --------------------------------------------------------

    @log_unzer_error
    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        customer = self.customer_from_order_skel(order_skel)
        customer = self.client.createOrUpdateCustomer(customer)
        logger.debug(f"{customer=} [RESPONSE]")

        return_url = self.get_return_url(order_skel)

        # Klarna (BNPL) cannot be charged directly; authorize it first.
        payment = self.client.authorize(
            unzer.PaymentRequest(
                self.get_payment_type(order_skel),
                amount=order_skel["total"],
                returnUrl=return_url,
                customerId=customer.key,
                orderId=order_skel["key"].id_or_name,
                invoiceId=order_skel["order_uid"],
                basketId=self.get_basket_id(order_skel),
            )
        )
        logger.debug(f"{payment=} [authorize response]")
        unzer_session = current.session.get()["unzer"] = {
            "customer_id": customer.key,
            "paymentId": payment.paymentId,
            "redirectUrl": payment.redirectUrl,
        }
        logger.debug(f"{unzer_session=}")
        current.session.get().markChanged()

        def set_payment(skel: SkeletonInstance):
            skel["payment"]["payments"][-1]["payment_id"] = payment.paymentId

        order_skel = toolkit.set_status(
            key=order_skel["key"],
            values=set_payment,
            skel=order_skel,
        )

        return unzer_session

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, t.Any]:
        """Capture the authorized Klarna payment on return, then report state.

        Klarna is only authorized during checkout (the customer approves the
        payment at the redirect). Once the customer returns, the authorization
        can be captured. If :attr:`charge_directly` is set, any authorized but
        not-yet-captured payment is charged here before the paid-state is
        evaluated by the base implementation.

        :param order_skel: OrderSkel to check.
        :return: A tuple ``(is_paid, payment-data)``.
        """
        is_paid, payment = super().check_payment_state(order_skel)
        if is_paid or not self.charge_directly:
            return is_paid, payment
        payments = payment if isinstance(payment, list) else [payment]
        if any(self.is_authorized_uncharged(p, order_skel) for p in payments):
            self.charge(order_skel=order_skel)
            return super().check_payment_state(order_skel)
        return is_paid, payment

    def is_authorized_uncharged(
        self,
        payment: unzer.PaymentGetResponse,
        order_skel: SkeletonInstance,
    ) -> bool:
        """Whether a payment holds a successful authorization but no capture yet."""
        if payment.state == PaymentState.COMPLETED:
            return False
        if payment.amountCharged and payment.amountCharged >= order_skel["total"]:
            return False
        return any(
            txn.action == "authorize" and txn.status == "success"
            for txn in payment.transactions
        )

    def charge(
        self,
        order_skel: SkeletonInstance,
        payment: PaymentResponse | None = None,
    ) -> tuple[SkeletonInstance, PaymentResponse]:
        if payment is None:
            payment = self.client.getPayment(order_skel["payment"]["payments"][-1]["payment_id"])
        payment = payment.charge(amount=order_skel["total"])
        logger.debug(f"{payment=} [charge response]")
        return order_skel, payment

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.Klarna(key=type_id)
