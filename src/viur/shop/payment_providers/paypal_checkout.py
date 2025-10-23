import logging
import typing as t

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
from viur.core import errors, exposed
from viur.core.skeleton import SkeletonInstance

from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..types import JsonResponse

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

    def check_payment_state(self):
        raise errors.NotImplemented()

    @exposed
    def return_handler(self):
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()

    @exposed
    def capture_order(self, order_id):
        """
        Capture payment for the created order to complete the transaction.

        @see https://developer.paypal.com/docs/api/orders/v2/#orders_capture
        """
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
