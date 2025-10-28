import logging
import typing as t  # noqa

from apimatic_core.utilities.api_helper import ApiHelper
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.controllers.payments_controller import PaymentsController
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from viur.core import access, current, db, errors, exposed
from viur.core.skeleton import SkeletonInstance

from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..types import InvalidStateError, JsonResponse, error_handler

logger = SHOP_LOGGER.getChild(__name__)


class PayPalCheckout(PaymentProviderAbstract):
    """
    PayPal Checkout integration for the ViUR Shop.

    Supports multiple payment methods through PayPal Checkout, including PayPal, credit card, and more.
    Handles the checkout process, payment state checks, and webhook handling for payment updates.
    """

    name: t.Final[str] = "paypal_checkout"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        sandbox: bool = False,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._sandbox = sandbox
        self.client: PaypalServersdkClient = PaypalServersdkClient(
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                o_auth_client_id=client_id,
                o_auth_client_secret=client_secret,
            ),
            logging_configuration=LoggingConfiguration(
                log_level=logging.INFO,
                # Disable masking of sensitive headers for Sandbox testing.
                # This should be set to True (the default if unset)in production.
                mask_sensitive_headers=not sandbox,
                request_logging_config=RequestLoggingConfiguration(
                    log_headers=True, log_body=True
                ),
                response_logging_config=ResponseLoggingConfiguration(
                    log_headers=True, log_body=True
                ),
            ),
        )

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> dict[str, t.Any]:
        return {
            "public_key": self._client_id,
            "sandbox": self._sandbox,
        }

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        orders_controller: OrdersController = self.client.orders
        payments_controller: PaymentsController = self.client.payments

        """
        Create an order to start the transaction.

        @see https://developer.paypal.com/docs/api/orders/v2/#orders_create
        """

        # request_body = request.get_json()
        # # use the cart information passed from the front-end to calculate the order amount detals
        # cart = request_body["cart"]
        order = orders_controller.create_order(
            {
                "body": OrderRequest(
                    intent=CheckoutPaymentIntent.CAPTURE,
                    purchase_units=[
                        PurchaseUnitRequest(
                            amount=AmountWithBreakdown(
                                currency_code="EUR",
                                value=order_skel["total"],
                                # breakdown=AmountBreakdown(
                                #     item_total=Money(currency_code="EUR", value=order_skel["total"])
                                # ),
                            ),
                            # items=[
                            #     Item(
                            #         name="T-Shirt",
                            #         unit_amount=Money(currency_code="EUR", value="100"),
                            #         quantity="1",
                            #         description="Super Fresh Shirt",
                            #         sku="sku01",
                            #         category=ItemCategory.PHYSICAL_GOODS,
                            #     )
                            # ],
                            reference_id=str(order_skel["key"].id_or_name),
                            custom_id=order_skel["order_uid"],
                            invoice_id=order_skel["order_uid"],
                        )
                    ],

                )
            }
        )
        logger.debug(f"Order created: {order}.")
        logger.debug(f"{order=}")
        logger.debug(f"{order.body=}")
        # logger.debug(f"{ApiHelper.json_serialize(order.body)=}")
        logger.debug(f"{ApiHelper.json_serialize(order.body, should_encode=False)=}")
        # logger.debug(f"{ApiHelper.to_dictionary(order.body)=}")
        return ApiHelper.json_serialize(order.body, should_encode=False)

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
        # TODO: Add params check_specific_payment_by_uuid
    ) -> tuple[bool, t.Any | list[t.Any]]:
        payment_results = []
        for idx, payment_src in enumerate(order_skel["payment"]["payments"], start=1):
            if not (payment_id := payment_src.get("payment_id") or payment_src.get("order_id")):
                logger.error(f"Payment #{idx} has no payment_id")
                continue
                raise InvalidStateError(f"Payment #{idx} has no payment_id")
                # Fetch by order short key (orderId)
                order_id = str(order_skel["key"].id_or_name)
                logger.debug(f"{order_id=}")
                payment = self.client.getPayment(order_id)
                logger.debug(f"{payment=}")
                order = None
            else:
                logger.debug(f"{payment_id=}")

                order = self.client.orders.get_order(dict(id=payment_id))
                logger.info(f"order: {order!r}")

            payment_results.append(order)

            logger.info(f"{order["status"]=!r}")
            assert len(order["purchase_units"]) == 1, len(order["purchase_units"])
            purchase_unit = order["purchase_units"][0]
            logger.info(f"{purchase_unit["status"]=!r}")

            assert len(purchase_unit["payments"]["captures"]) == 1, len(purchase_unit["payments"]["captures"])
            capture = purchase_unit["capture"][0]
            logger.info(f"{capture["status"]=!r}")

            # TODO
            assert float(capture["amount"]["value"]) == order_skel["total"]
            assert capture["invoice_id"] == order_skel["order_uid"]
            assert capture["status"] == "COMPLETED"

            # if str(payment.invoiceId) != str(order_skel["order_uid"]):
            #     raise e.InvalidStateError(f'{payment.invoiceId} != {order_skel["order_uid"]}')
            #
            # if payment.state == PaymentState.COMPLETED and payment.amountCharged == order_skel["total"]:
            #     return True, payment

            return True, order

        return False, payment_results

        order = self.client.orders.get_order(dict(id=payment_src["order_id"]))
        logger.info(f"order: {order!r}")

        return None, []  # TODO

    @exposed
    def return_handler(self):
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    @access("root")
    @error_handler
    def get_debug_information(
        self,
        *,
        order_key: db.Key | str | None = None,
        payment_id: str | None = None,
    ) -> JsonResponse[list[dict[str, t.Any]]]:
        """Get information about a payment / order.

        :param order_key: Key of the order skeleton.
        :param payment_id: PayPal ID of the order / payment.
        """
        if payment_id is not None:
            payments = [{"payment_id": payment_id}]
            skel = None
        else:
            if order_key is None:
                if not (order_key := self.shop.order.current_session_order_key):
                    raise errors.BadRequest("No order_key or payment_id given")
            skel = self.shop.order.skel().read(key=order_key)
            payments = skel["payment"]["payments"]

        result = []
        for payment_src in payments:
            if not (payment_id := payment_src.get("order_id")):
                result.append({
                    "error": "order_id missing",
                })
                continue
            if (client_id := payment_src.get("client_id")) and client_id != self._client_id:
                result.append({
                    "error": "client_id does not match client's client_id",
                    "client_id_payment": client_id,
                    "client_id_client": self._client_id,
                })
                continue
            logger.info(f"Checking payment {payment_id=}:")

            order = self.client.orders.get_order(dict(id=payment_src["order_id"]))
            logger.info(f"order: {order!r}")

            #
            # logger.info(f"payment: {payment!r}")
            # txn = payment.getChargedTransactions()
            # logger.info(f"charged transactions: {txn!r}")
            # customer = payment.customerId and self.client.getCustomer(payment.customerId)
            # logger.info(f"customer: {customer!r}")
            # basket = payment.basketId and self.client.getBasket(payment.basketId)
            # logger.info(f"basket: {basket!r}")

            result.append({
                "order": ApiHelper.json_serialize(order.body, should_encode=False),
                # "payment": dict(payment),
                # "transactions": [dict(t) for t in txn],
                # "customer": customer and dict(customer),
                # "basket": basket and dict(basket),
            })

        result = {
            "payments": result,
            "payment_state": skel and self.check_payment_state(skel),
        }

        return JsonResponse(result)
        return JsonResponse(self.model_to_dict(result))

    @exposed
    @error_handler
    def capture_order(
        self,
        order_key: str | db.Key,
        order_id: str,
    ):
        """
        Capture payment for the created order to complete the transaction.

        @see https://developer.paypal.com/docs/api/orders/v2/#orders_capture
        """

        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.editSkel()
        if not order_skel.read(order_key):
            raise errors.NotFound

        order_skel = self._append_payment_to_order_skel(
            order_skel,
            {
                "client_id": self._client_id,
                "order_id": order_id,
                "payment_id": order_id,
                "charged": False,  # TODO: Set value
                "aborted": False,  # TODO: Set value
                "client_ip": current.request.get().request.client_addr,
                "user_agent": current.request.get().request.user_agent,
            }
        )
        # return JsonResponse(order_skel)

        orders_controller: OrdersController = self.client.orders
        order = orders_controller.capture_order(
            {"id": order_id, "prefer": "return=representation"}
        )
        logger.debug(f"Order {order_id} captured successfully.")
        logger.debug(f"{order=}")
        logger.debug(f"{order.body=}")

        return JsonResponse(
            ApiHelper.json_serialize(order.body, should_encode=False)
        )
