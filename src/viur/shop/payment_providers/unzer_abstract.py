import abc
import typing as t  # noqa

import unzer
from unzer.model import PaymentType
from unzer.model.customer import Salutation as UnzerSalutation
from unzer.model.payment import PaymentState

from viur.core import current, db, errors, exposed, utils
from viur.core.skeleton import SkeletonInstance
from viur.shop.types import *
from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER
from ..types import exceptions as e

logger = SHOP_LOGGER.getChild(__name__)


class UnzerAbstract(PaymentProviderAbstract):

    def __init__(
        self,
        *,
        private_key: str,
        public_key: str,
        sandbox: bool = False,
        language: str = "en",
    ):
        super().__init__()
        self.private_key = private_key
        self.public_key = public_key
        self.sandbox = sandbox
        self.language = language
        self.client = unzer.UnzerClient(
            private_key=self.private_key,
            public_key=self.public_key,
            sandbox=self.sandbox,
            language=self.language,
        )
        # logger.debug(f"{self.client.getKeyPair() = }")

    def can_checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> list[ClientError]:
        errs = []
        if not order_skel["billing_address"]:
            errs.append(ClientError("billing_address is missing"))
        if not order_skel["cart"] or not order_skel["cart"]["dest"]["shipping_address"]:
            errs.append(ClientError("cart.shipping_address is missing"))
        return errs

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

        # TODO: write in transaction
        order_skel["payment"]["payments"][-1]["payment_id"] = payment.paymentId
        order_skel.toDB()

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
        # TODO: if payment is prepared ...
        errs = []
        return errs

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, unzer.PaymentGetResponse]:
        payment_id = order_skel["payment"]["payments"][-1]["payment_id"]
        logger.debug(f"{payment_id = }")
        payment = self.client.getPayment(payment_id)
        logger.debug(f"{payment = }")
        # payment.charge(order_skel["total"])
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
            self.shop.order.set_paid(order_skel)
            # order_skel["is_paid"] = True  # TODO: transaction
            # order_skel.toDB()
        else:
            raise errors.NotImplemented("Order not paid")
        return "OKAY, paid"

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()

    @exposed
    def save_type(
        self,
        order_key: str | db.Key,
        type_id: str,
    ):
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        order_skel = self.shop.order.editSkel()
        if not order_skel.fromDB(order_key):
            raise errors.NotFound
        if not order_skel["payment"]:
            order_skel["payment"] = {}
        order_skel["payment"].setdefault("payments", []).append({
            "pp": self.name,
            "creationdate": utils.utcNow().isoformat(),
            "type_id": type_id,
            "charged": False,
            "aborted": False,
        })
        order_skel.toDB()

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
            email=order_skel["email"],
            # TODO: phone=order_skel["phone"],
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
