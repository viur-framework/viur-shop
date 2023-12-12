import logging

from viur.core.bones import *
from viur.core.skeleton import Skeleton

logger = logging.getLogger("viur.shop").getChild(__name__)


def get_suppliers() -> dict[str, str]:
    return {}
    return shop.configured_supliers  # TODO


class ShippingSkel(Skeleton):
    kindName = "shop_shipping"

    name = StringBone(
        descr="Name",
    )

    description = TextBone(
        descr="Name",
    )

    shipping_cost = NumericBone(
        descr="Rate",
    )

    supplier = SelectBone(
        descr="supplier",
        values=get_suppliers,
    )
