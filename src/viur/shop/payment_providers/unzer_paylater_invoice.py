import typing as t
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

import unzer
from unzer.model import PaymentType
from viur.core.skeleton import SkeletonInstance

from .unzer_abstract import UnzerAbstract, log_unzer_error
from ..globals import SHOP_LOGGER

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
        customer = self.customer_from_order_skel(order_skel)
        logger.debug(f"{customer = }")

        customer = self.client.createOrUpdateCustomer(customer)
        logger.debug(f"{customer = } [RESPONSE]")

        host = current.request.get().request.host_url
        return_url = f'{host.rstrip("/")}/{self.modulePath.strip("/")}/return_handler?order_key={order_skel["key"].to_legacy_urlsafe().decode("ASCII")}'
        unzer_session = current.session.get()["unzer"] = {
            "customer_id": customer.key,
        }
        payment = self.client.authorize(
            # TODO: x-CLIENTIP=<YOUR Client's IP>
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
        logger.debug(f"{payment=} [authorize response]")
        unzer_session["paymentId"] = payment.paymentId
        unzer_session["redirectUrl"] = payment.redirectUrl
        processing_data = payment.processing.asDict()

        payment = payment.charge(
            amount=order_skel["total"]
        )
        logger.debug(f"{payment=} [charge response]")

        logger.debug(f"{unzer_session = }")
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



    def get_payment_type(
        self,
        order_skel: SkeletonInstance,
    ) -> PaymentType:
        type_id = order_skel["payment"]["payments"][-1]["type_id"]
        return unzer.PaylaterInvoice(key=type_id)
