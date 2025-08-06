import abc
import enum
import functools
import json
import typing as t  # noqa

import unzer
from unzer.model import PaymentType
from unzer.model.base import BaseModel
from unzer.model.customer import Salutation as UnzerSalutation
from unzer.model.payment import PaymentState
from unzer.model.webhook import Events, IP_ADDRESS
from viur import toolkit
from viur.core import CallDeferred, access, current, db, errors, exposed, force_post
from viur.core.skeleton import SkeletonInstance
from viur.shop.skeletons import OrderSkel
from viur.shop.types import *

from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..services import HOOK_SERVICE, Hook
from ..types import exceptions as e

logger = SHOP_LOGGER.getChild(__name__)

P = t.ParamSpec("P")
R = t.TypeVar("R")


def log_unzer_error(func: t.Callable[P, R]) -> t.Callable[P, R]:
    """
    Decorator to log unzer errors

    Decorator that logs details of an unzer.model.ErrorResponse if raised,
    then re-raises the error.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except unzer.model.ErrorResponse as err:
            logger.error(f"Unzer ErrorResponse encountered in {func.__qualname__}")
            logger.error(f"ErrorResponse: {err!r}")
            for idx, error in enumerate(err.errors, start=1):
                logger.error(f"  #{idx} {error!r}")
            raise err

    return wrapper


class UnzerClientViURShop(unzer.UnzerClient):

    def __init__(
        self,
        private_key: str | t.Callable[[], str],
        public_key: str | t.Callable[[], str],
        sandbox: bool | t.Callable[[], bool] = False,
        language: str = "en",
    ):
        # completely overwritten to keep properties
        super(unzer.UnzerClient, self).__init__()
        self._private_key = private_key
        self._public_key = public_key
        self._sandbox = sandbox
        self.language = language

    @property
    def private_key(self) -> str:
        if callable(self._private_key):
            return self._private_key()
        return self._private_key

    @property
    def public_key(self) -> str:
        if callable(self._public_key):
            return self._public_key()
        return self._public_key

    @property
    def sandbox(self) -> bool:
        if callable(self._sandbox):
            return self._sandbox()
        return self._sandbox

    def _request(self, url, method, headers, payload, auth):
        # Extend with ViUR Logic:
        # Before the request is performed, we update the accept-language with
        # the language of the current request, unless it has been explicitly set.
        if self.language is None:
            # language for translation of customerMessage in errors
            headers["accept-language"] = current.language.get()

        return super()._request(url, method, headers, payload, auth)


class UnzerAbstract(PaymentProviderAbstract):
    """
    Abstract base class for Unzer payment methods in the ViUR Shop.

    Provides common functionality for Unzer-based payment providers,
    including API communication and payment type handling.
    """

    def __init__(
        self,
        *,
        private_key: str | t.Callable[[], str],
        public_key: str | t.Callable[[], str],
        sandbox: bool | t.Callable[[], bool] = False,
        language: str | None = None,
        **kwargs: t.Any,
    ) -> None:
        """
        Create a new Unzer payment provider.

        :param private_key: The private key to use for authentication.
        :param public_key: The public key to use for authentication.
        :param sandbox: Use sandbox mode (development mode).
        :param language: Enforce this language. If ``None``, the language of the current request is used.
        """
        super().__init__(**kwargs)
        self._private_key = private_key
        self._public_key = public_key
        self._sandbox = sandbox
        self.language = language
        self.client = UnzerClientViURShop(
            private_key=private_key,
            public_key=public_key,
            sandbox=sandbox,
            language=self.language,
        )
        # logger.debug(f"{self.client.getKeyPair() = }")

    @property
    def private_key(self) -> str:
        if callable(self._private_key):
            return self._private_key()
        return self._private_key

    @property
    def public_key(self) -> str:
        if callable(self._public_key):
            return self._public_key()
        return self._public_key

    @property
    def sandbox(self) -> bool:
        if callable(self._sandbox):
            return self._sandbox()
        return self._sandbox

    def can_checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> list[ClientError]:
        errs = super().can_checkout(order_skel)
        if not order_skel["billing_address"]:
            errs.append(ClientError("billing_address is missing"))
        if not order_skel["cart"] or not order_skel["cart"]["dest"]["shipping_address"]:
            errs.append(ClientError("cart.shipping_address is missing"))
        return errs

    @log_unzer_error
    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        customer = self.customer_from_order_skel(order_skel)
        logger.debug(f"{customer = }")

        customer = self.client.createOrUpdateCustomer(customer)
        logger.debug(f"{customer = } [RESPONSE]")

        host = current.request.get().request.host_url
        return_url = f'{host.rstrip("/")}/{self.modulePath.strip("/")}/return_handler?order_key={order_skel["key"].to_legacy_urlsafe().decode("ASCII")}'
        unzer_session = current.session.get()["unzer"] = {
            "customer_id": customer.key,
        }
        payment = self.client.charge(
            unzer.PaymentRequest(
                self.get_payment_type(order_skel),
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

        def set_payment(skel: SkeletonInstance):
            skel["payment"]["payments"][-1]["payment_id"] = payment.paymentId

        order_skel = toolkit.set_status(
            key=order_skel["key"],
            values=set_payment,
            skel=order_skel,
        )

        return unzer_session

    @abc.abstractmethod
    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        ...

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        return {
            "public_key": self.public_key,
            "sandbox": self.sandbox,
        }

    def can_order(
        self,
        order_skel: SkeletonInstance,
    ) -> list[ClientError]:
        errs = []

        # logger.debug(f'{order_skel=}')
        logger.debug(f'{order_skel["key"]=} | {order_skel["payment"]=}')

        if not order_skel["payment"] or not order_skel["payment"].get("payments"):
            errs.append(ClientError("payment is missing"))
            # TODO: if payment is prepared and not aborted, type matches ...

        return errs

    def charge(self):
        raise errors.NotImplemented()

    def get_order_by_pay_id(
        self,
        payment_id: str,
        public_key: str,
        *args, **kwargs
    ) -> SkeletonInstance_T[OrderSkel] | None:
        """Helper method to get the order skel for a payment-id.

        :param payment_id: The payment id. (ex: s-pay-1).
        :param public_key: Public key of the key pair.

        :return: The order-skel if the key seems valid. None otherwise.
        """
        logger.debug(f"get_order_by_pay_id({payment_id=} | {public_key=})")

        if public_key != self.client.public_key:
            logger.error(f"Got {public_key=}, expected {self.client.public_key}")
            raise PermissionError(f"Public key {public_key} does not match with the current client configuration")

        payment = self.client.getPayment(payment_id)
        logger.debug(f"Found {payment=!r}")

        order_skel = self.shop.order.skel()
        if not order_skel.read(payment.orderId):
            logger.warning(f"Cannot load order skel with {payment.orderId=}. Not from us?")
            return None

        return order_skel

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
        # TODO: Add params check_specific_payment_by_uuid
    ) -> tuple[bool, unzer.PaymentGetResponse | list[unzer.PaymentGetResponse]]:
        """
        Get the payment state for a order.

        Checks all payments stored in order_skel["payment"]["payments"] for
        a completed and full charge.

        In case of a completed charge, only the payment data of the charged payment is returned.
        Otherwise (failed or missing payment), data of all payments is returned.

        :param order_skel: OrderSkel SkeletonInstance to check
        :return: A tuple: [is_paid-boolean, payment-data]
        """
        payment_results = []
        for idx, payment_src in enumerate(order_skel["payment"]["payments"], start=1):
            if not (payment_id := payment_src.get("payment_id")):
                logger.error(f"Payment #{idx} has no payment_id")
                # Fetch by order short key (orderId)
                order_id = str(order_skel["key"].id_or_name)
                logger.debug(f"{order_id=}")
                payment = self.client.getPayment(order_id)
                logger.debug(f"{payment=}")
            else:
                logger.debug(f"{payment_id=}")
                payment = self.client.getPayment(payment_id)
                logger.debug(f"{payment=}")
            payment_results.append(payment)

            if str(payment.invoiceId) != str(order_skel["order_uid"]):
                raise e.InvalidStateError(f'{payment.invoiceId} != {order_skel["order_uid"]}')

            if payment.state == PaymentState.COMPLETED and payment.amountCharged == order_skel["total"]:
                return True, payment

        return False, payment_results

    @exposed
    @log_unzer_error
    def return_handler(
        self,
        order_key: db.Key,
    ) -> t.Any:
        """Return Endpoint

        Endpoint to which customers are redirected once they have processed a payment on the payment server.
        """
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
        else:
            return HOOK_SERVICE.dispatch(Hook.PAYMENT_RETURN_HANDLER_ERROR)(order_skel, payment)
        return HOOK_SERVICE.dispatch(Hook.PAYMENT_RETURN_HANDLER_SUCCESS)(order_skel, payment)

    @exposed
    @force_post
    def webhook(self, *args, **kwargs):
        """Webhook for unzer.

        Listens to all events, but handle payment-complete as backup currently only.
        """
        try:
            payload = json.loads(current.request.get().request.body)
        except ValueError:
            raise errors.BadRequest("Invalid payload")
        logger.info(f"Received request via webhook. {args=}, {kwargs=}")
        logger.info(f"{payload=}")
        logger.info(f"headers={dict(current.request.get().request.headers)!r}")

        ip = current.request.get().request.remote_addr
        logger.info(f"{ip=}")
        if ip not in IP_ADDRESS:
            logger.warning(f"Unallowed IP address {ip}")
            raise errors.Forbidden

        if payload.get("event") == Events.PAYMENT_COMPLETED:
            order_skel = self.get_order_by_pay_id(payload["paymentId"], payload["publicKey"])
            if not order_skel:
                raise errors.BadRequest("Unknown order")
            # Do this with a delay, otherwise there may be an interference with the return_hook
            logger.info(f'Check payment for {order_skel["key"]!r} deferred')
            self.check_payment_deferred(order_skel["key"], _countdown=60)

        current.request.get().response.status = "204 No Content"
        return ""

    @CallDeferred
    @log_unzer_error
    def check_payment_deferred(self, order_key: db.Key) -> None:
        """Check the status for an unzer payment deferred"""
        order_skel = self.shop.order.skel().read(order_key)
        is_paid, payment = self.check_payment_state(order_skel)
        if is_paid and order_skel["is_paid"]:
            logger.info(f'Order {order_skel["key"]!r} already marked as paid. Nothing to do.')
        elif is_paid:
            logger.info(f'Mark order {order_skel["key"]!r} as paid')
            self.shop.order.set_paid(order_skel)
        else:
            logger.info(f'Order {order_skel["key"]!r} is not paid')

    @exposed
    @access("root")
    def get_debug_information(
        self,
        *,
        order_key: db.Key | str | None = None,
        payment_id: str | None = None,
    ) -> JsonResponse[list[dict[str, t.Any]]]:
        """Get information about a payment / order.

        :param order_key: Key of the order skeleton.
        :param payment_id: Unzer ID of the order / payment.
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
            if (public_key := payment_src.get("public_key")) and public_key != self.client.public_key:
                result.append({
                    "error": "public_key does not match client's public_key",
                    "public_key_payment": public_key,
                    "public_key_client": self.client.public_key,
                })
                continue
            logger.info(f"Checking payment {payment_id=}:")
            payment = self.client.getPayment(payment_id)
            logger.info(f"payment: {payment!r}")
            txn = payment.getChargedTransactions()
            logger.info(f"charged transactions: {txn!r}")
            customer = payment.customerId and self.client.getCustomer(payment.customerId)
            logger.info(f"customer: {customer!r}")
            basket = payment.basketId and self.client.getBasket(payment.basketId)
            logger.info(f"basket: {basket!r}")

            result.append({
                "payment": dict(payment),
                "transactions": [dict(t) for t in txn],
                "customer": customer and dict(customer),
                "basket": basket and dict(basket),
            })

        result = {
            "payments": result,
            "payment_state": skel and self.check_payment_state(skel),
        }

        return JsonResponse(self.model_to_dict(result))

    @exposed
    @log_unzer_error
    def save_type(
        self,
        order_key: str | db.Key,
        type_id: str,
    ):
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.editSkel()
        if not order_skel.read(order_key):
            raise errors.NotFound

        order_skel = self._append_payment_to_order_skel(
            order_skel,
            {
                "public_key": self.public_key,
                "type_id": type_id,
                "charged": False,  # TODO: Set value
                "aborted": False,  # TODO: Set value
            }
        )
        return JsonResponse(order_skel)

    # --- utils ---------------------------------------------------------------

    def customer_from_order_skel(
        self,
        order_skel: SkeletonInstance,
    ) -> unzer.Customer:
        ba = order_skel["billing_address"]["dest"]
        sa = order_skel["cart"]["dest"]["shipping_address"]["dest"]

        return unzer.Customer(
            firstname=ba["firstname"],
            lastname=ba["lastname"],
            salutation=self.shop_salutation_to_unzer_salutation(ba["salutation"]),
            customerId=self.customer_id_from_order_skel(order_skel),
            email=ba["email"],
            phone=ba["phone"],
            billingAddress=self.address_from_address_skel(ba),
            shippingAddress=self.address_from_address_skel(sa),
        )

    def customer_id_from_order_skel(
        self,
        order_skel: SkeletonInstance,
    ) -> str:
        # TODO: use key of the OrderSkel or AddressSkel?
        prefix = "s" if self.client.sandbox else "p"
        return f'{prefix}{order_skel["key"].id_or_name}'

    def address_from_address_skel(
        self,
        address_skel: SkeletonInstance,
    ) -> unzer.Address:
        logger.debug(f"{address_skel = } ({type(address_skel)})")
        return unzer.Address(
            firstname=address_skel["firstname"],
            lastname=address_skel["lastname"],
            street=f'{address_skel["street_name"]} {address_skel["street_number"]}',
            # TODO: combine this street in the AddressSkel via @property order ComputedBone
            zipCode=address_skel["zip_code"],
            city=address_skel["city"],
            country=address_skel["country"] and address_skel["country"].upper(),
        )

    @staticmethod
    def shop_salutation_to_unzer_salutation(
        salutation: Salutation
    ) -> UnzerSalutation:
        return {
            Salutation.MALE: UnzerSalutation.MR,
            Salutation.FEMALE: UnzerSalutation.MRS,
            Salutation.OTHER: UnzerSalutation.UNKNOWN,  # TODO
        }.get(salutation, UnzerSalutation.UNKNOWN)

    @classmethod
    def model_to_dict(cls, obj):
        """Convert any nested unzer model to dict representation"""
        if isinstance(obj, BaseModel):
            obj = dict(obj)  # Convert to dict first, then process recursively
        if isinstance(obj, dict):
            return {k: cls.model_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list | tuple):
            return [cls.model_to_dict(v) for v in obj]
        elif isinstance(obj, enum.Enum):
            return f"{obj!r}"
        return obj
