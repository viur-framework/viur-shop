import logging

from viur.core import current, db, exposed
from viur.core.prototypes import List
from .abstract import ShopModuleAbstract
from .. import exceptions as e
from ..constants import AddressType
from ..response_types import JsonResponse
from ..skeletons.order import get_payment_providers

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
