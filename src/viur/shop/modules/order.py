import logging

from viur.core import current, db
from viur.core.prototypes import List
from .abstract import ShopModuleAbstract
from ..constants import AddressType
from .. import exceptions as e

logger = logging.getLogger("viur.shop").getChild(__name__)


class Order(ShopModuleAbstract, List):
    kindName = "shop_order"

    def order_add(
        self,
        cart_key: db.Key,
        payment_provider: str = None,
        billing_address_key: db.Key = None,
        email: str = None,
        customer_key: db.Key = None,
        state_ordered: bool = None,
        state_paid: bool = None,
        state_rts: bool = None,
        # TODO: use sentinel as in cart
    ):
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")
        if not isinstance(billing_address_key, (db.Key, type(None))):
            raise TypeError(f"billing_address_key must be an instance of db.Key")
        if not isinstance(customer_key, (db.Key, type(None))):
            raise TypeError(f"customer_key must be an instance of db.Key")
        skel = self.addSkel()
        cart_skel = self.shop.cart.viewSkel("node")
        if not self.shop.cart.is_valid_node(cart_key, root_node=True):
            raise ValueError(f"Invalid {cart_key=}!")
        skel.setBoneValue("cart", cart_key)
        skel["total"] = cart_skel["total"]
        if "payment_provider" in current.request.get().kwargs:
            skel["payment_provider"] = payment_provider  # TODO: validate
        if "billing_address_key" in current.request.get().kwargs:
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
        if "email" in current.request.get().kwargs:
            skel["email"] = email
        if "customer_key" in current.request.get().kwargs:
            skel.setBoneValue("customer", customer_key)  # TODO: validate (must be self of an admin)
        # TODO(discussion): Do we really want to set this by the frontend?
        #  Or what are the pre conditions?
        if "state_ordered" in current.request.get().kwargs:
            skel["state_ordered"] = state_ordered
        if "state_paid" in current.request.get().kwargs:
            skel["state_paid"] = state_paid
        if "state_rts" in current.request.get().kwargs:
            skel["state_rts"] = state_rts
        skel.toDB()
        if cart_key == self.shop.cart.current_session_cart_key:
            # This is now a order basket and should no longer be modified
            self.shop.cart.detach_session_cart()
        return skel
