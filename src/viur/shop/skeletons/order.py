import logging

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.constants import *

logger = logging.getLogger("viur.shop").getChild(__name__)


def get_payment_providers() -> dict[str, str]:
    return {}
    return shop.payment_providers  # TODO


class OrderSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_order"

    billing_address = RelationalBone(
        descr="billing_address",
        kind="shop_address",
    )

    customer = RelationalBone(
        descr="customer",
        kind="user",
    )

    cart = RelationalBone(
        descr="cart",
        kind="shop_cart_node",
    )

    total = NumericBone(
        descr="total",
        precision=2,
        min=0,
        # TODO: UnitBone / CurrencyBone
    )
    """Kopie der total vom gesamten Warenkorb"""

    order_uid = StringBone(
        descr="order_uid",
    )
    """Bestellnummer"""

    payment_provider = SelectBone(
        descr="payment_provider",
        values=get_payment_providers,
    )

    is_ordered = BooleanBone(
        descr="is_ordered",
    )

    is_paid = BooleanBone(
        descr="is_paid",
    )

    is_rts = BooleanBone(
        descr="is_rts",
    )

    state = SelectBone(
        descr="state",
        values=OrderState,
        multiple=True,
        # compute=Compute(), #TODO:tbd; generate from is_* bones
    )

    email = EmailBone(
        descr="email",
    )
    """Kopieren von User oder Eingabe von Nutzer bei Gast"""

    project_data = JsonBone(
        descr="project_data",
    )
    """Zusätzliche Daten vom Projekt für eine Bestellung.
    Ggf. überlegen ob einzelne Bones durch Skeleton Modifizierung besser sind."""
