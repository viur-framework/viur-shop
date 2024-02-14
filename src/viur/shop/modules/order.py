import logging
import time
import typing as t

from viur.core import current, db, errors as core_errors, exposed, force_post
from viur.core.prototypes import List

from .abstract import ShopModuleAbstract
from .. import exceptions as e
from ..constants import AddressType
from ..payment_providers import PaymentProviderAbstract
from ..response_types import JsonResponse
from ..skeletons.order import get_payment_providers

if t.TYPE_CHECKING:
    from viur.core.skeleton import SkeletonInstance

logger = logging.getLogger("viur.shop").getChild(__name__)

_sentinel = object()


class Order(ShopModuleAbstract, List):
    kindName = "shop_order"

    @exposed
    def payment_providers_list(self):
        return JsonResponse(get_payment_providers())

    def order_add(
        self,
        cart_key: db.Key,
        payment_provider: str = _sentinel,
        billing_address_key: db.Key = _sentinel,
        email: str = _sentinel,
        customer_key: db.Key = _sentinel,
        state_ordered: bool = _sentinel,
        state_paid: bool = _sentinel,
        state_rts: bool = _sentinel,
    ):
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")
        if billing_address_key is not _sentinel and not isinstance(billing_address_key, (db.Key, type(None))):
            raise TypeError(f"billing_address_key must be an instance of db.Key")
        if customer_key is not _sentinel and not isinstance(customer_key, (db.Key, type(None))):
            raise TypeError(f"customer_key must be an instance of db.Key")
        skel = self.addSkel()
        cart_skel = self.shop.cart.viewSkel("node")
        if not self.shop.cart.is_valid_node(cart_key, root_node=True):
            raise ValueError(f"Invalid {cart_key=}!")
        assert cart_skel.fromDB(cart_key)
        skel.setBoneValue("cart", cart_key)
        skel["total"] = cart_skel["total"]
        if payment_provider is not _sentinel:
            skel["payment_provider"] = payment_provider  # TODO: validate
        if billing_address_key is not _sentinel:
            if billing_address_key is None:
                skel["billing_address"] = None
            else:
                skel.setBoneValue("billing_address", billing_address_key)
                if skel["billing_address"]["dest"]["address_type"] != AddressType.BILLING:
                    raise e.InvalidArgumentException(
                        "shipping_address",
                        descr_appendix="Address is not of type billing."
                    )
        if user := current.user.get():
            # us current user as default value
            skel["email"] = user["name"]
            skel.setBoneValue("customer", user["key"])
        if email is not _sentinel:
            skel["email"] = email
        if customer_key is not _sentinel:
            skel.setBoneValue("customer", customer_key)  # TODO: validate (must be self of an admin)
        # TODO(discussion): Do we really want to set this by the frontend?
        #  Or what are the pre conditions?
        if state_ordered is not _sentinel:
            skel["state_ordered"] = state_ordered
        if state_paid is not _sentinel:
            skel["state_paid"] = state_paid
        if state_rts is not _sentinel:
            skel["state_rts"] = state_rts
        skel.toDB()
        if cart_key == self.shop.cart.current_session_cart_key:
            # This is now an order basket and should no longer be modified
            self.shop.cart.detach_session_cart()
        return skel

    def order_update(
        self,
        order_key: db.Key,
        payment_provider: str = _sentinel,
        billing_address_key: db.Key = _sentinel,
        email: str = _sentinel,
        customer_key: db.Key = _sentinel,
        state_ordered: bool = _sentinel,
        state_paid: bool = _sentinel,
        state_rts: bool = _sentinel,
    ):
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        if billing_address_key is not _sentinel and not isinstance(billing_address_key, (db.Key, type(None))):
            raise TypeError(f"billing_address_key must be an instance of db.Key")
        if customer_key is not _sentinel and not isinstance(customer_key, (db.Key, type(None))):
            raise TypeError(f"customer_key must be an instance of db.Key")
        skel = self.editSkel()
        if not skel.fromDB(order_key):
            raise core_errors.NotFound
        # TODO: refactor duplicate code!
        if payment_provider is not _sentinel:
            skel["payment_provider"] = payment_provider  # TODO: validate
        if billing_address_key is not _sentinel:
            if billing_address_key is None:
                skel["billing_address"] = None
            else:
                skel.setBoneValue("billing_address", billing_address_key)
                if skel["billing_address"]["dest"]["address_type"] != AddressType.BILLING:
                    raise e.InvalidArgumentException(
                        "shipping_address",
                        descr_appendix="Address is not of type billing."
                    )
        if user := current.user.get():
            # us current user as default value
            skel["email"] = user["name"]
            skel.setBoneValue("customer", user["key"])
        if email is not _sentinel:
            skel["email"] = email
        if customer_key is not _sentinel:
            skel.setBoneValue("customer", customer_key)  # TODO: validate (must be self of an admin)
        # TODO(discussion): Do we really want to set this by the frontend?
        #  Or what are the pre conditions?
        if state_ordered is not _sentinel:
            skel["state_ordered"] = state_ordered
        if state_paid is not _sentinel:
            skel["state_paid"] = state_paid
        if state_rts is not _sentinel:
            skel["state_rts"] = state_rts
        skel.toDB()
        return skel

    @exposed
    @force_post
    def checkout_start(
        self,
        order_key: db.Key,
    ):
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        order_skel = self.editSkel()
        if not order_skel.fromDB(order_key):
            raise core_errors.NotFound()
        order_skel.refresh()  # TODO: cart.shipping_address relation seems not be updated by the core
        if errors := self.can_checkout(order_skel):
            logging.error(errors)
            return JsonResponse({
                "errors": errors,
            }, status_code=400)
            raise e.InvalidStateError(", ".join(errors))

        order_skel = self.freeze_order(order_skel)
        order_skel.toDB()
        return JsonResponse({
            "skel": order_skel,
            "payment": self.get_payment_provider_by_name(order_skel["payment_provider"]).get_checkout_start_data(
                order_skel),
        })

    def can_checkout(
        self,
        order_skel: "SkeletonInstance",
    ) -> list["ErrorClassTBD"]:  # TODO
        errors = []
        if not order_skel["cart"]:
            errors.append("cart is missing")
        if not order_skel["payment_provider"]:
            errors.append("missing payment_provider")
        if pp_errors := self.get_payment_provider_by_name(order_skel["payment_provider"]).can_checkout(order_skel):
            errors.extend(pp_errors)

        # TODO: ...
        return errors

    def freeze_order(
        self,
        order_skel: "SkeletonInstance",
    ) -> "SkeletonInstance":
        # TODO:
        #  - recalculate cart
        #  - copy values (should not be hit by update relations)
        self.shop.cart.freeze_cart(order_skel["cart"]["dest"]["key"])

        cart_skel = self.shop.cart.viewSkel("node")
        assert cart_skel.fromDB(order_skel["cart"]["dest"]["key"])
        order_skel["total"] = cart_skel["total"]

        # Clone the address, so in case the user edits the address, existing orders wouldn't be affected by this
        # TODO: Can we do this copy-on-write instead; clone if an address is edited and replace on used order skels?
        ba_skel = self.shop.address.editSkel()
        ba_key = order_skel["billing_address"]["dest"]["key"]
        assert ba_skel.fromDB(ba_key)
        # Remove the key to clone it #  TODO: why does this not work?
        # ba_skel.dbEntity.key = None
        # ba_skel.accessedValues.pop("key", None)
        # ba_skel.boneMap = ba_skel.boneMap.copy()
        old_ba_ske = ba_skel
        # create a new instance and copy all values except the jey
        ba_skel = self.shop.address.addSkel()
        for name, value in old_ba_ske.items(True):
            if name == "key":
                continue
            ba_skel[name] = value
        ba_skel.setBoneValue("cloned_from", ba_key)
        # logger.debug(f"{order_skel = }")
        key = ba_skel.toDB()
        # logger.debug(f"{key = } // {ba_skel = }")
        assert ba_skel["key"] != ba_key, \
            f'{ba_skel["key"]} != {ba_key}'
        order_skel.setBoneValue("billing_address", ba_skel["key"])
        order_skel.toDB()

        return order_skel

    def assign_uid(
        self,
        order_skel: "SkeletonInstance",
    ) -> "SkeletonInstance":
        order_skel["order_uid"] = "".join(
            f"-{c}" if i % 4 == 0 else c
            for i, c in enumerate(str(time.time()).replace(".", ""))
        ).strip("-")
        # TODO: customize by hook, claim in transaction, ...
        return order_skel

    @exposed
    @force_post
    def checkout_order(
        self,
        order_key: db.Key,
    ):
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        order_skel = self.editSkel()
        if not order_skel.fromDB(order_key):
            raise core_errors.NotFound()

        if errors := self.can_order(order_skel):
            logging.error(errors)
            return JsonResponse({
                "errors": errors,
            }, status_code=400)
            raise e.InvalidStateError(", ".join(error_))

        order_skel = self.assign_uid(order_skel)
        order_skel["is_ordered"] = True
        # TODO: call hooks
        # TODO: charge order if it should directly be charged
        pp_res = self.get_payment_provider_by_name(order_skel["payment_provider"]).checkout(order_skel)
        # TODO: write in transaction
        order_skel.toDB()
        return JsonResponse({
            "skel": order_skel,
            "payment": pp_res,
        })

    def can_order(
        self,
        order_skel: "SkeletonInstance",
    ) -> list["ErrorClassTBD"]:  # TODO
        errors = []
        if order_skel["is_ordered"]:
            errors.append("already is_ordered")
        if not order_skel["cart"]:
            errors.append("cart is missing")
        if not order_skel["cart"] or not order_skel["cart"]["dest"]["shipping_address"]:
            errors.append("cart.shipping_address is missing")
        if not order_skel["payment_provider"]:
            errors.append("missing payment_provider")
        if not order_skel["billing_address"]:
            errors.append("billing_address is missing")
        if pp_errors := self.get_payment_provider_by_name(order_skel["payment_provider"]).can_order(order_skel):
            errors.extend(pp_errors)

        # TODO: ...
        return errors

    # --- Internal helpers  ----------------------------------------------------
    def get_payment_provider_by_name(
        self,
        payment_provider_name: str,
    ) -> PaymentProviderAbstract:
        for pp in self.shop.payment_providers:
            if payment_provider_name == pp.name:
                return pp
        raise LookupError(f"Unknown payment provider {payment_provider_name}")
