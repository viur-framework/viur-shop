import logging

from viur.core.bones import *
from viur.core.skeleton import Skeleton

logger = logging.getLogger("viur.shop").getChild(__name__)


def get_suppliers() -> dict[str, str]:
    return {}
    return shop.configured_supliers  # TODO


class ShippingSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_shipping"

    name = StringBone(
        descr="Name",
    )
    """DHL Standard, DHL Express, DPD-Shop, ..."""

    description = TextBone(
        descr="description",
        validHtml=None,
    )
    """
    "Sie brauchen ein DHL-Kundenkonto"
    "Du bist auf einer Insel"
    ...
    """

    shipping_cost = NumericBone(
        descr="shipping_cost",
        precision=2,
        min=0,
    )

    supplier = SelectBone(
        descr="supplier",
        values=get_suppliers,
    )

    delivery_time_min = NumericBone(
        descr="delivery_time_min",
        min=0,
        # TODO: UnitBone
    )
    """Tag(e)"""

    delivery_time_max = NumericBone(
        descr="delivery_time_max",
        min=0,
        # TODO: UnitBone
    )
    """Tag(e)"""
