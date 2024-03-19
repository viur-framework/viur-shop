import typing as t  # noqa

from viur.core.bones import *
from viur.core.i18n import translate
from viur.core.skeleton import Skeleton
from ..globals import SHOP_LOGGER, SHOP_INSTANCE

logger = SHOP_LOGGER.getChild(__name__)


def get_suppliers() -> dict[str, str]:
    return {
        supplier.key: supplier.name
        for supplier in SHOP_INSTANCE.get().suppliers
    }


class ShippingSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_shipping"

    name = StringBone(
    )
    """DHL Standard, DHL Express, DPD-Shop, ..."""

    description = TextBone(
        validHtml=None,
    )
    """
    "Sie brauchen ein DHL-Kundenkonto"
    "Du bist auf einer Insel"
    ...
    """

    shipping_cost = NumericBone(
        precision=2,
        min=0,
        getEmptyValueFunc=lambda: None,
    )

    supplier = SelectBone(
        values=get_suppliers,
    )

    delivery_time_min = NumericBone(
        min=0,
        # TODO: UnitBone
    )
    """Tag(e)"""

    delivery_time_max = NumericBone(
        min=0,
        # TODO: UnitBone
    )
    """Tag(e)"""
