import logging
import typing as t

import unzer
from unzer.model.customer import Salutation as UnzerSalutation

from viur.core import db, errors, exposed, utils
from viur.core.skeleton import SkeletonInstance
from . import PaymentProviderAbstract
from .. import Salutation
from ..response_types import JsonResponse

logger = logging.getLogger("viur.shop").getChild(__name__)


class UnzerAbstract(PaymentProviderAbstract):

    def __init__(
        self,
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
        logger.debug(f"{self.client.getKeyPair() = }")

    def can_checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
        errs = []
        if not order_skel["billing_address"]:
            errs.append("billing_address is missing")
        return errs

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        raise errors.NotImplemented()

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        return {
            "public_key": self.public_key,
        }

    def can_order(
        self,
        order_skel: SkeletonInstance,
    ) -> list["Error"]:
        # TODO: if payment is prepared ...
        return []

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
