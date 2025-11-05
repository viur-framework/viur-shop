import enum
import json
import logging
import typing as t  # noqa

from apimatic_core.utilities.api_helper import ApiHelper
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.http.api_response import ApiResponse
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order import Order
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.order_status import OrderStatus
from paypalserversdk.models.purchase_unit import PurchaseUnit
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from viur.core import access, current, db, errors, exposed, force_post
from viur.core.skeleton import SkeletonInstance

from viur import toolkit
from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..skeletons import OrderSkel
from ..types import (
    InvalidStateError,
    JsonResponse,
    PaymentTransaction,
    SkeletonInstance_T,
    error_handler,
)

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
                # This should be set to True (the default if unset) in production.
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
        order_skel: SkeletonInstance_T[OrderSkel],
    ) -> t.Any:
        """
        Create an order to start the transaction.

        @see https://developer.paypal.com/docs/api/orders/v2/#orders_create
        """
        order = self.client.orders.create_order(
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
                            reference_id=str(order_skel["key"].id_or_name),
                            custom_id=str(order_skel["key"].id_or_name),
                            invoice_id=order_skel["order_uid"],
                        )
                    ],
                )
            }
        )
        # TODO: store this order.id -- it's the payment_id
        logger.debug(f"Order created: {order}.")
        logger.debug(f"{order.body=}")
        logger.debug(f"{ApiHelper.json_serialize(order.body, should_encode=False)=}")

        order_skel = self._append_payment_to_order_skel(
            order_skel,
            PaymentTransaction(**{
                "client_id": self._client_id,
                "order_id": order.body.id,
                "payment_id": order.body.id,
                "charged": False,  # TODO: Set value
                "aborted": False,  # TODO: Set value
            })
        )

        return ApiHelper.json_serialize(order.body, should_encode=False)

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
        # TODO: Add params check_specific_payment_by_uuid
    ) -> tuple[bool, t.Any | list[t.Any]]:
        payment_results = []
        payment_src: PaymentTransaction
        for idx, payment_src in enumerate(order_skel["payment"]["payments"], start=1):
            payment_id = payment_src["payment_id"]
            logger.debug(f"{payment_id=}")

            order: ApiResponse = self.client.orders.get_order(dict(id=payment_id))
            logger.info(f"order: {order!r}")
            order: Order = order.body
            payment_results.append(order)

            logger.info(f"{toolkit.vars_full(order)=!r}")
            logger.info(f"{order.status=!r}")

            if order.status != OrderStatus.COMPLETED:
                logger.info(f"Payment #{idx} is not completed ({order.status=!r})")
                continue  # This payment is incomplete

            if (purchase_units_length := len(order.purchase_units)) != 1:
                logger.info(f"Payment #{idx} has an invalid amount of purchase_units ({purchase_units_length=})")
                continue  # This payment is invalid

            purchase_unit: PurchaseUnit = order.purchase_units[0]
            logger.debug(f"{purchase_unit=!r}")

            if not hasattr(purchase_unit, "payments"):
                logger.info(f"Payment #{idx} has purchase_unit(s), but without payment ({purchase_unit=})")
                continue  # This payment is incomplete

            logger.debug(f"{purchase_unit.payments=!r}")
            logger.debug(f"{purchase_unit.payments.captures=!r}")

            if (captures_length := len(purchase_unit.payments.captures)) != 1:
                logger.info(
                    f"Payment #{idx} has purchase_unit(s) with an invalid amount of captures ({captures_length=})")
                continue  # This payment is invalid

            capture = purchase_unit.payments.captures[0]
            logger.info(f"{capture.status=!r}")

            if capture.invoice_id != order_skel["order_uid"]:
                logger.info(f"Payment #{idx} has a capture that does not match the order_uid "
                            f"({capture.invoice_id=} != {order_skel["order_uid"]=})")
                continue

            if capture.status != OrderStatus.COMPLETED:
                logger.info(f"Payment #{idx} has a capture that is not completed ({capture.status=!r})")
                continue  # This payment is incomplete

            if capture.invoice_id != order_skel["order_uid"]:
                logger.info(f"Payment #{idx} has a capture that does not match the order_uid "
                            f"({capture.invoice_id=} != {order_skel["order_uid"]=})")
                continue

            if capture.invoice_id != order_skel["order_uid"]:
                logger.error(f"Payment #{idx} has a fully captured payment, but amount does not match"
                             f"({capture.amount.value=} != {order_skel["total"]})")
                raise InvalidStateError(f"Payment #{idx} has been captured with invalid amount")

            return True, order

        return False, payment_results

    @exposed
    def return_handler(self):
        raise errors.NotImplemented()

    @exposed
    @force_post
    @error_handler
    def webhook(self, *args, **kwargs):
        """Webhook for PayPal.

        Listens to all events, but handle payment-complete as backup currently only.
        """
        try:
            payload = json.loads(current.request.get().request.body)
        except ValueError:
            raise errors.BadRequest("Invalid payload")
        logger.info(f"Received request via webhook. {args=}, {kwargs=}")
        logger.info(f"{payload=}")
        logger.info(f"headers={dict(current.request.get().request.headers)!r}")

        # ip = current.request.get().request.remote_addr
        # logger.info(f"{ip=}")
        # if ip not in IP_ADDRESS:
        #     logger.warning(f"Unallowed IP address {ip}")
        #     raise errors.Forbidden

        if payload.get("event_type") == "PAYMENT.CAPTURE.COMPLETED":
            custom_id = payload["resource"]["custom_id"]
            invoice_id = payload["resource"]["invoice_id"]

            order_skel = self.shop.order.skel()
            if not order_skel.read(custom_id):
                logger.warning(f"Cannot load order skel with {custom_id=} (short-key). Not from us?")
                if not (order_skel := order_skel.all().filter("order_uid =", invoice_id).getSkel()):
                    logger.warning(f"Cannot load order skel with {invoice_id=} (order_uid). Not from us?")
                    raise errors.BadRequest("Unknown order")

            # Do this with a delay, otherwise there may be an interference with the return_hook
            logger.info(f'Check payment for {order_skel["key"]!r} deferred')
            self.check_payment_deferred(order_skel["key"], _countdown=60)

        current.request.get().response.status = "204 No Content"
        return ""

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
            if not (payment_id := payment_src.get("payment_id")):
                result.append({
                    "error": "payment_id missing",
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

            result.append({
                "order": order.body,
            })

        result = {
            "payments": payments,
            "payment_state": skel and self.check_payment_state(skel),
        }

        return JsonResponse(self.model_to_dict(result))

    @exposed
    @error_handler
    def capture_order(
        self,
        order_key: str | db.Key,
        order_id: str,
    ) -> JsonResponse[dict[str, dict[str, t.Any]]]:
        """
        Capture payment for the created order to complete the transaction.

        @see https://developer.paypal.com/docs/api/orders/v2/#orders_capture
        """
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.editSkel()
        if not order_skel.read(order_key):
            raise errors.NotFound

        for idx, payment_src in enumerate(order_skel["payment"]["payments"], start=1):
            if (payment_id := payment_src["payment_id"]) == order_id:
                logger.info(f"payment #{idx} {payment_id=}: {payment_src=}")
                # TODO: set charged
                break
        else:
            raise InvalidStateError(f"payment {order_id=} not found")

        orders_controller: OrdersController = self.client.orders
        order = orders_controller.capture_order({
            "id": order_id,
            "prefer": "return=representation",
        })
        logger.debug(f"Order {order_id} captured successfully.")
        logger.debug(f"{order.body=}")

        self.check_payment_deferred(order_skel["key"], _call_deferred=False)
        order_skel.read(order_key)  # refresh

        return JsonResponse({
            "skel": order_skel,
            "payment": ApiHelper.json_serialize(order.body, should_encode=False),
        })

    @classmethod
    def model_to_dict(cls, obj):
        """Convert any nested PayPal model to dict representation"""
        obj = ApiHelper.json_serialize(obj, should_encode=False)  # Convert to dict first, then process recursively
        if isinstance(obj, dict):
            return {k: cls.model_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list | tuple):
            return [cls.model_to_dict(v) for v in obj]
        elif isinstance(obj, enum.Enum):
            return f"{obj!r}"
        return obj
