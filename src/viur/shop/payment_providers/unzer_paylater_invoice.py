import functools
import typing as t  # noqa

import unzer

from viur import toolkit
from viur.core import current, db, errors, exposed
from viur.core.skeleton import SkeletonInstance
from viur.shop.skeletons import OrderSkel
from viur.shop.types import *
from .unzer_abstract import UnzerAbstract, log_unzer_error
from ..globals import MAX_FETCH_LIMIT, SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class UnzerPaylaterInvoice(UnzerAbstract):
    """
    Unzer Paylater Invoice payment method integration for the ViUR Shop.

    Enables customers to pay using invoice through the Unzer payment gateway.
    """

    name: t.Final[str] = "unzer-paylater_invoice"

    def can_order(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
    ) -> list[ClientError]:
        order_skel = OrderSkel.refresh_billing_address(order_skel)
        errs = super().can_order(order_skel)
        if not order_skel["billing_address"] or not order_skel["billing_address"]["dest"]["birthdate"]:
            errs.append(ClientError("billing_address has no birthday set"))
        return errs

    @log_unzer_error
    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        order_skel = OrderSkel.refresh_billing_address(order_skel)
        if not order_skel["billing_address"]["dest"]["birthdate"]:
            raise errors.PreconditionFailed("Billing address has no birthdate")

        # Paylater invoice cannot be charged directly.
        # Therefore, we must authorize them first before charging them.
        payment = self.client.authorize(
            self.get_payment_request(order_skel),
            headers={
                "x-CLIENTIP": current.request.get().request.client_addr,
            },
        )
        unzer_session = current.session.get()["unzer"] = {
            "customer_id": payment.customerId,
        }
        logger.debug(f"{payment=} [authorize response]")
        unzer_session["paymentId"] = payment.paymentId
        unzer_session["redirectUrl"] = payment.redirectUrl
        processing_data = payment.processing.asDict()

        payment = payment.charge(
            amount=order_skel["total"]
        )
        logger.debug(f"{payment=} [charge response]")

        logger.debug(f"{unzer_session=}")
        current.session.get().markChanged()

        def set_payment(skel: SkeletonInstance):
            skel["payment"]["payments"][-1]["payment_id"] = payment.paymentId
            skel["payment"]["payments"][-1]["processing_data"] = processing_data

        order_skel = toolkit.set_status(
            key=order_skel["key"],
            values=set_payment,
            skel=order_skel,
        )

        return unzer_session

    def get_customer(self, order_skel: SkeletonInstance) -> unzer.Customer:
        customer = self.customer_from_order_skel(order_skel)
        logger.debug(f"{customer=}")
        customer = self.client.createOrUpdateCustomer(customer)
        logger.debug(f"{customer=} [RESPONSE]")
        return customer

    def get_payment_request(self, order_skel: SkeletonInstance) -> unzer.PaymentRequest:
        customer = self.get_customer(order_skel)
        host = current.request.get().request.host_url
        return_url = (f'{host.rstrip("/")}/{self.modulePath.strip("/")}/return_handler'
                      f'?order_key={order_skel["key"].to_legacy_urlsafe().decode("ASCII")}')
        return unzer.PaymentRequest(
            self.get_payment_type(order_skel),
            amount=order_skel["total"],
            returnUrl=return_url,
            card3ds=True,
            customerId=customer.key,
            orderId=order_skel["key"].id_or_name,
            invoiceId=order_skel["order_uid"],
            additional_transaction_data=unzer.AdditionalTransactionData(
                risk_data=self.get_risk_data(order_skel),
            )
        )

    def get_risk_data(self, order_skel: SkeletonInstance) -> unzer.RiskData:
        risk_data = unzer.RiskData(
            registrationLevel=(unzer.RegistrationLevel.GUEST if order_skel["customer"] is None
                               else unzer.RegistrationLevel.REGISTERED),
            customerGroup=unzer.CustomerGroup.NEUTRAL
        )
        if order_skel["customer"] is not None:
            risk_data.registrationDate = order_skel["customer"]["dest"]["creationdate"]
            orders = (
                self.shop.order.skel(bones=("is_paid", "total")).all()
                .filter("customer.dest.__key__ =", order_skel["customer"]["dest"]["key"])
                .filter("is_paid =", True)
                .fetch(MAX_FETCH_LIMIT)
            )
            risk_data.confirmedOrders = len(orders)
            risk_data.confirmedAmount = functools.reduce(lambda total, skel: total + skel["total"], orders, 0)
        return risk_data

    @exposed
    @log_unzer_error
    def risk_check(
        self,
        # order_skel: SkeletonInstance_T[OrderSkel],
        order_key: db.Key,
    ) -> t.Any:
        """Customer Risk Check Endpoint

        Do a risk check for the customer.
        Customer risk check is an optional step after the payment method is selected.
        It is used for the risk evaluation of the end customer data.
        When sending the request, you must also add the x-CLIENTIP=<YOUR Client's IP> attribute in the header.
        This operation is not part of the payment process. Like credit card check,
        it is used to pre-check customer data immediately
        after the payment method selection step in the checkout.
        This way customer receives direct feedback before finishing the order,
        avoiding irritation.
        The riskCheck request contains customer resource’s reference and transactional details.
        """
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.viewSkel()
        if not order_skel.read(order_key):
            raise errors.NotFound
        order_skel = OrderSkel.refresh_billing_address(order_skel)
        return JsonResponse(
            self.model_to_dict(
                self.client.request(
                    f"types/paylater-invoice/risk-check",
                    "POST",
                    self.get_payment_request(order_skel).serialize(),
                    additional_headers={
                        "x-CLIENTIP": current.request.get().request.client_addr,
                    },
                )
            )
        )

    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> unzer.PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.PaylaterInvoice(key=type_id)
