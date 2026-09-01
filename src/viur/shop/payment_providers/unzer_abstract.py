import abc
import functools
import json
import typing as t  # noqa

import unzer
from unzer.model import Basket, BasketItem, PaymentType
from unzer.model.base import BaseModel
from unzer.model.customer import Salutation as UnzerSalutation
from unzer.model.payment import PaymentState
from unzer.model.webhook import Events, IP_ADDRESS

from viur import toolkit
from viur.core import access, current, db, errors, exposed, force_post
from viur.core.skeleton import SkeletonInstance
from viur.shop.skeletons import OrderSkel
from viur.shop.types import *
from . import PaymentProviderAbstract
from ..globals import MAX_FETCH_LIMIT, SHOP_LOGGER
from ..services import HOOK_SERVICE, Hook
from ..skeletons.cart import CartNodeSkel
from ..types import error_handler, exceptions as e

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
        client_ip: str = None,
    ):
        # completely overwritten to keep properties
        super(unzer.UnzerClient, self).__init__()
        self._private_key = private_key
        self._public_key = public_key
        self._sandbox = sandbox
        self.language = language
        self.client_ip = client_ip

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

    currency_code: str = "EUR"
    """Currency the basket amounts are reported in."""

    # Unzer basket item types (serialized as ``type``).
    BASKET_ITEM_GOODS: t.Final[str] = "goods"
    BASKET_ITEM_SHIPMENT: t.Final[str] = "shipment"
    BASKET_ITEM_VOUCHER: t.Final[str] = "voucher"

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

    # --- Internal Checks & Actions during the payment flow -------------------

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

        return_url = self.get_return_url(order_skel)
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
    ) -> dict[str, t.Any]:
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

    def charge(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
        payment: t.Any | None = None,
    ) -> tuple[SkeletonInstance_T[OrderSkel], t.Any]:
        raise errors.NotImplemented(f"charge method not implemented in {type(self)}")

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
        payment_src: PaymentTransaction
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

    # --- API Endpoints  ------------------------------------------------------

    @exposed
    @log_unzer_error
    @error_handler
    def return_handler(
        self,
        order_key: db.Key,
    ) -> t.Any:
        """Return Endpoint

        Endpoint to which customers are redirected once they have processed a payment on the payment server.
        """
        # TODO: move to abstract?
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
    @log_unzer_error
    @error_handler
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

    # TODO: remove
    '''
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
    '''

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
    @error_handler
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
            PaymentTransaction(**{
                "public_key": self.public_key,
                "type_id": type_id,
                "charged": False,  # TODO: Set value
                "aborted": False,  # TODO: Set value
            })
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
            birthDate=ba["birthdate"],
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
    def model_to_dict(cls, obj: t.Any) -> t.Any:
        """Convert any nested unzer model to dict representation"""
        if isinstance(obj, BaseModel):
            obj = dict(obj)  # Convert to dict first, then process recursively
        return super().model_to_dict(obj)

    def get_customer(self, order_skel: SkeletonInstance) -> unzer.Customer:
        customer = self.customer_from_order_skel(order_skel)
        logger.debug(f"{customer=}")
        customer = self.client.createOrUpdateCustomer(customer)
        logger.debug(f"{customer=} [RESPONSE]")
        return customer

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

    # --- Basket --------------------------------------------------------------

    def get_basket_id(
        self,
        order_skel: SkeletonInstance,
    ) -> str:
        """Build a basket from the order's cart and create it at Unzer.

        Klarna requires a basket whose line items reconcile to the order
        total. The basket is built from the entire cart tree and created via
        the Unzer API; the returned basket id is passed to the authorize
        request.

        :param order_skel: The order to derive the basket from.
        :return: The id of the created Unzer basket.
        """
        basket_items = self.build_basket_items(order_skel)
        basket = Basket(
            amountTotalGross=order_skel["total"],
            amountTotalDiscount=toolkit.round_decimal(
                sum(item.amountDiscount or 0.0 for item in basket_items), 2),
            currencyCode=self.currency_code,
            orderId=order_skel["key"].id_or_name,
            basketItems=basket_items,
        )
        return self.client.createBasket(basket).key

    def build_basket_items(
        self,
        order_skel: SkeletonInstance,
    ) -> list[BasketItem]:
        """Collect the whole cart tree as Unzer basket items.

        The cart is a tree in which every node may apply its own shipping and
        (basket-domain) discount on top of the accumulated subtree total
        ("decorator" principle). The item grosses therefore reconcile exactly to
        ``order_skel["total"]`` (== root ``total_discount_price``).

        :param order_skel: The order whose cart is converted.
        :return: The basket items for the complete cart.
        """
        # The order's cart ref lacks the ``discount`` bone we need for
        # node-level discounts, so read the root node skeleton fully.
        root_skel = self.shop.cart.viewSkel("node")
        if not root_skel.read(order_skel["cart"]["dest"]["key"]):
            raise ValueError(f'Cannot read root cart node for order {order_skel["key"]!r}')

        basket_items, _ = self.build_node_items(root_skel)
        return basket_items

    def build_node_items(
        self,
        node_skel: SkeletonInstance,
    ) -> tuple[list[BasketItem], float]:
        """Convert one cart node's subtree into basket items.

        Mirrors the ``total_discount_price`` computation of :class:`CartNodeSkel`
        (see ``add_discount`` / ``add_shipping`` in ``skeletons.cart``): the
        node's discount applies to the accumulated subtree — its own article
        leaves plus the already discounted totals of its child nodes, including
        their shipping — while its *own* shipping is added afterwards and stays
        undiscounted.

        The discount *amount* is not recomputed from the discount skeleton but
        taken as the difference between the items and the node's stored
        ``total_discount_price``. An ordered cart is frozen, so that stored value
        is what the customer is charged even if the discount changed afterwards —
        and it keeps the basket reconciling to ``order_skel["total"]`` whatever
        the discount type does. Discounts of nested nodes accumulate on the
        articles below them, innermost first.

        :param node_skel: The cart node to convert.
        :return: The items of this subtree, and the node's
            ``total_discount_price``.
        """
        discountable: list[BasketItem] = []
        base = 0.0
        for child in self.shop.cart.get_children(node_skel["key"]):
            if issubclass(child.skeletonCls, CartNodeSkel):
                child_items, child_total = self.build_node_items(child)
                discountable.extend(child_items)
                base += child_total
            else:
                item = self.build_article_item(child)
                discountable.append(item)
                base += item.amountGross
        # The total bones round at every node, so the discount base has to as well.
        base = toolkit.round_decimal(base, 2)

        shipping_item = self.build_shipping_item(node_skel)
        node_total = toolkit.round_decimal(node_skel["total_discount_price"] or 0.0, 2)
        # The node's own shipping is added after the discount, so back it out again.
        discounted_base = toolkit.round_decimal(
            node_total - (shipping_item.amountGross if shipping_item else 0.0), 2)
        amount = toolkit.round_decimal(base - discounted_base, 2)

        if amount < 0:
            logger.error(
                f'Cart node {node_skel["key"]!r} costs {-amount} more than its items '
                f"({base} vs {discounted_base}); the basket will not add up"
            )
        elif self.has_basket_discount(node_skel):
            self.spread_discount(discountable, amount)
        elif amount:
            logger.error(
                f'Cart node {node_skel["key"]!r} is {amount} off its items '
                f"({base} vs {discounted_base}) without carrying a basket discount"
            )

        items = discountable if shipping_item is None else [*discountable, shipping_item]
        return items, node_total

    def build_article_item(
        self,
        leaf_skel: SkeletonInstance,
    ) -> BasketItem:
        """Convert a single cart leaf (article) into an Unzer basket item.

        Article-level discounts are already contained in ``price_.current``;
        basket-level discounts are spread over the items afterwards, see
        :meth:`spread_discount`.

        :param leaf_skel: The cart item (leaf) to convert.
        :return: The corresponding Unzer basket item.
        """
        price = leaf_skel.price_
        quantity = int(leaf_skel["quantity"])
        return BasketItem(
            basketItemReferenceId=leaf_skel["key"].id_or_name,
            title=leaf_skel["shop_name"] or leaf_skel["key"].id_or_name,
            quantity=quantity,
            kind=self.BASKET_ITEM_GOODS,
            vat=round(price.vat_rate_percentage * 100),
            amountPerUnit=price.current_net,
            amountNet=toolkit.round_decimal(price.current_net * quantity, 2),
            amountVat=toolkit.round_decimal(price.vat_included * quantity, 2),
            amountGross=toolkit.round_decimal(price.current * quantity, 2),
        )

    def build_shipping_item(
        self,
        node_skel: SkeletonInstance,
    ) -> BasketItem | None:
        """Build the shipping basket item for a cart node, if any.

        :param node_skel: The cart node whose shipping is converted.
        :return: The shipping basket item, or ``None`` if the node has no
            (chargeable) shipping.
        """
        if not (shipping := node_skel["shipping"]):
            return None
        gross = shipping["dest"]["shipping_cost"] or 0.0
        if not gross:
            return None
        # Shipping is taxed at the standard rate (see cart.get_vat_for_node).
        vat_percent = self.get_shipping_vat_percentage(node_skel)
        net = Price.gross_to_net(gross, vat_percent / 100.0)
        return BasketItem(
            basketItemReferenceId=f'shipping-{node_skel["key"].id_or_name}',
            title=shipping["dest"]["name"] or "Shipping",
            quantity=1,
            kind=self.BASKET_ITEM_SHIPMENT,
            vat=round(vat_percent),
            amountPerUnit=toolkit.round_decimal(net, 2),
            amountNet=toolkit.round_decimal(net, 2),
            amountVat=toolkit.round_decimal(gross - net, 2),
            amountGross=toolkit.round_decimal(gross, 2),
        )

    @staticmethod
    def has_basket_discount(
        node_skel: SkeletonInstance,
    ) -> bool:
        """Whether the node carries a discount that reduces its total.

        Mirrors :func:`skeletons.cart.add_discount`: only basket-domain discounts
        reduce the node total, article-domain ones are already reflected in the
        article prices.

        :param node_skel: The cart node to inspect.
        :return: ``True`` if a basket-domain discount applies to this node.
        """
        if not (discount := node_skel["discount"]):
            return False
        return any(
            condition["dest"]["application_domain"] == ApplicationDomain.BASKET
            for condition in discount["dest"]["condition"]
        )

    @staticmethod
    def spread_discount(
        items: list[BasketItem],
        amount: float,
    ) -> None:
        """Spread a node discount over the items it applies to, in whole cents.

        Unzer refuses basket items with negative amounts, in both the v1 and the
        v3 schema (``API.600.200.131``, plus ``API.600.410.018`` on v1), so a
        discount cannot be sent as a negative line of its own. It has to be a
        positive ``amountDiscount`` on the items it reduces, which means the
        node discount has to be split up.

        The split is proportional to what is left of each item — its gross minus
        the discounts already spread on it by nested nodes — and is done in whole
        cents: every item gets the floor of its exact share, and the cents left
        over by rounding go to the items with the largest fractional part. The
        parts therefore add up to *amount* exactly, which matters because the v3
        basket endpoint reconciles the total to the cent (v1 does not check it at
        all, but the payment methods that hand the basket to a partner system
        may).

        ``amountGross``, ``amountNet`` and ``amountVat`` of an item stay at their
        pre-discount values; that is how the API stores them, the reduced value
        being ``amountGross - amountDiscount``.

        :param items: The items to spread over; modified in place.
        :param amount: The (positive) discount amount to spread.
        :raises ValueError: If the amount exceeds what the items can carry, which
            would force an item below zero.
        """
        if amount <= 0:
            return
        # An item can only carry a discount down to zero, so weigh by the
        # remainder after the discounts a nested node already spread on it.
        weights = [
            max(toolkit.round_decimal(item.amountGross - (item.amountDiscount or 0.0), 2), 0.0)
            for item in items
        ]
        spreadable = toolkit.round_decimal(sum(weights), 2)
        if amount > spreadable:
            raise ValueError(
                f"Cannot spread a discount of {amount} over items worth {spreadable}"
            )

        # Work in cents: floor each exact share, then hand out the remaining
        # cents by the largest fractional part (and never above an item's weight).
        cents = round(amount * 100)
        caps = [round(weight * 100) for weight in weights]
        exact = [cents * weight / spreadable for weight in weights]
        shares = [min(int(value), cap) for value, cap in zip(exact, caps)]
        order = sorted(
            range(len(items)),
            key=lambda idx: (exact[idx] - int(exact[idx]), weights[idx]),
            reverse=True,
        )
        # One cent per item and pass, so the remainder reaches as many items as there
        # are cents left. A pass can hand out fewer than it should when items are
        # capped, hence the loop; without any progress the amount does not fit, which
        # the check above should already have caught.
        while (left := cents - sum(shares)) > 0:
            progressed = False
            for idx in order:
                if left <= 0:
                    break
                if shares[idx] < caps[idx]:
                    shares[idx] += 1
                    left -= 1
                    progressed = True
            if not progressed:  # pragma: no cover - ruled out by the ValueError above
                raise ValueError(f"Cannot spread {amount} over items worth {spreadable}")

        for item, share in zip(items, shares):
            if share:
                item.amountDiscount = toolkit.round_decimal(
                    (item.amountDiscount or 0.0) + share / 100, 2)

    def get_shipping_vat_percentage(
        self,
        node_skel: SkeletonInstance,
    ) -> float:
        """Return the standard VAT percentage for a node's shipping.

        :param node_skel: The cart node providing the shipping country.
        :return: The standard VAT rate in percent (e.g. ``19.0``), or ``0.0``
            if none is configured.
        """
        try:
            # The referenced skeleton carries its own renderPreparation, which would
            # turn the select bone's value into a wrapper object instead of the code.
            country = toolkit.without_render_preparation(node_skel["shipping_address"]["dest"])["country"]
        except (AttributeError, KeyError, TypeError):
            country = None
        try:
            return self.shop.vat_rate.get_vat_rate_for_country(
                country=country, category=VatRateCategory.STANDARD,
            )
        except Exception as exc:  # noqa: BLE001 -- fall back to 0 % on any config error
            logger.warning(f"No standard vat rate for shipping: {exc}")
            return 0.0
