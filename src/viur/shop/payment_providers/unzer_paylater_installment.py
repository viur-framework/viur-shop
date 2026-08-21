import typing as t  # noqa

import unzer
from unzer import PaymentResponse

from viur import toolkit
from viur.core import current, errors
from viur.core.skeleton import SkeletonInstance
from viur.shop.skeletons import OrderSkel
from viur.shop.types import *
from .unzer_abstract import UnzerAbstract, log_unzer_error
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerPaylaterInstallment(UnzerAbstract):
    """Unzer Installment (Ratenkauf) for the ViUR Shop.

    Part of Unzer's Buy Now Pay Later offering, available in Germany, Austria and
    Switzerland. The customer picks a plan during the checkout and pays the purchase
    in monthly rates; Unzer collects them by direct debit.

    The plans are fetched and presented by the payment component in the frontend,
    which binds the customer's choice to the payment type resource. Nothing about the
    plan is therefore needed here -- only the type id the frontend reports back.

    Unzer offers no direct charge for this method: the payment is authorized during
    the checkout and charged on fulfillment, see :attr:`charge_directly`.
    """

    name: t.Final[str] = "unzer-paylater_installment"

    def __init__(
        self,
        *args: t.Any,
        charge_directly: bool = False,
        **kwargs: t.Any,
    ) -> None:
        """
        :param charge_directly: If ``True``, charge the authorized payment right after
            the checkout. Defaults to ``False``: an installment purchase is charged
            when the goods ship.
        """
        super().__init__(*args, **kwargs)
        self.charge_directly = charge_directly

    def can_order(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
    ) -> list[ClientError]:
        """Reject an order that cannot be authorized.

        Unzer runs a credit check on the customer, for which the date of birth is
        mandatory -- unlike for the payment methods that are charged right away.

        :param order_skel: OrderSkel to validate.
        :return: The errors that prevent ordering, empty if there are none.
        """
        order_skel = OrderSkel.refresh_billing_address(order_skel)
        errs = super().can_order(order_skel)
        if not order_skel["billing_address"] or not order_skel["billing_address"]["dest"]["birthdate"]:
            errs.append(ClientError("billing_address has no birthdate set"))
        return errs

    @log_unzer_error
    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        """Authorize the installment payment.

        Unzer offers no direct charge here: the purchase is authorized during the
        checkout and captured on fulfillment, unless :attr:`charge_directly` says
        otherwise. The order therefore stays unpaid when this returns.

        :param order_skel: OrderSkel to pay for.
        :return: The unzer session data, as stored in the current session.
        """
        order_skel = OrderSkel.refresh_billing_address(order_skel)
        if not order_skel["billing_address"]["dest"]["birthdate"]:
            raise errors.PreconditionFailed("Billing address has no birthdate")

        # Installment cannot be charged directly; authorize it first.
        payment = self.client.authorize(
            self.get_payment_request(order_skel),
            headers={
                "x-CLIENTIP": current.request.get().request.client_addr,
            },
        )
        logger.debug(f"{payment=} [authorize response]")
        unzer_session = current.session.get()["unzer"] = {
            "customer_id": payment.customerId,
            "paymentId": payment.paymentId,
            "redirectUrl": payment.redirectUrl,
        }
        logger.debug(f"{unzer_session=}")
        current.session.get().markChanged()

        processing_data = payment.processing.asDict()

        def set_payment(skel: SkeletonInstance) -> None:
            skel["payment"]["payments"][-1]["payment_id"] = payment.paymentId
            skel["payment"]["payments"][-1]["processing_data"] = processing_data

        order_skel = toolkit.set_status(
            key=order_skel["key"],
            values=set_payment,
            skel=order_skel,
        )

        if self.charge_directly:
            order_skel, payment = self.charge(order_skel=order_skel, payment=payment)

        return unzer_session

    def charge(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
        payment: PaymentResponse | None = None,
    ) -> tuple[SkeletonInstance_T[OrderSkel], PaymentResponse]:
        """Capture the authorized payment, in full.

        :param order_skel: OrderSkel the payment belongs to.
        :param payment: (optional) The payment to charge. Defaults to the payment of
            the order's last payment attempt.
        :return: The order and the charged payment.
        """
        if payment is None:
            payment = self.client.getPayment(order_skel["payment"]["payments"][-1]["payment_id"])
        payment = payment.charge(amount=order_skel["total"])
        logger.debug(f"{payment=} [charge response]")
        return order_skel, payment

    def get_payment_request(
        self,
        order_skel: SkeletonInstance,
    ) -> unzer.PaymentRequest:
        """Build the authorize request.

        Installment requires a basket resource whose line items reconcile to the
        order total, and risk data about the customer.

        :param order_skel: The order to be authorized.
        :return: The request to authorize.
        """
        customer = self.get_customer(order_skel)
        return unzer.PaymentRequest(
            self.get_payment_type(order_skel),
            amount=order_skel["total"],
            returnUrl=self.get_return_url(order_skel),
            customerId=customer.key,
            orderId=order_skel["key"].id_or_name,
            invoiceId=order_skel["order_uid"],
            basketId=self.get_basket_id(order_skel),
            additional_transaction_data=unzer.AdditionalTransactionData(
                risk_data=self.get_risk_data(order_skel),
            ),
        )

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> unzer.PaymentType:
        """Build the payment type from the resource the frontend created.

        The resource already carries the plan the customer picked and their IBAN,
        so the type id is all that is needed here.

        :param order_skel: OrderSkel holding the payment attempt.
        :return: The installment payment type to authorize.
        """
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.PaylaterInstallment(key=type_id)
