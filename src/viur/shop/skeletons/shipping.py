import functools
import typing as t  # noqa

from viur.core.bones import *
from viur.core.i18n import translate
from viur.core.skeleton import Skeleton
from ..globals import SHOP_INSTANCE, SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


def get_suppliers() -> dict[str, str]:
    return {
        supplier.key: supplier.name
        for supplier in SHOP_INSTANCE.get().suppliers
    }


def is_empty(self: NumericBone, value: t.Any):
    """0 is not empty function"""
    # logger.debug(f"{self.getEmptyValue()=} | {value=}")
    if isinstance(value, str) and not value:
        return True
    try:
        value = self._convert_to_numeric(value)
    except (ValueError, TypeError):
        return True
    return value is None


class ShippingSkel(Skeleton):
    kindName = "{{viur_shop_modulename}}_shipping"

    name = StringBone(
        searchable=True,
        escape_html=False,
    )
    """DHL Standard, DHL Express, DPD-Shop, ..."""

    description = TextBone(
        validHtml=None,
        params={
            "tooltip": translate(
                "viur.shop.skeleton.shipping.description.tooltip",
                public=True,
            ),
        },
        searchable=True,
    )
    """
    "Sie brauchen ein DHL-Kundenkonto"
    "Du bist auf einer Insel"
    ...
    """

    shipping_cost = NumericBone(
        precision=2,
        min=0,
        defaultValue=0,
        # getEmptyValueFunc=lambda: None,
        isEmptyFunc=is_empty,
    )
    shipping_cost.isEmpty = functools.partial(is_empty, shipping_cost)  # Re-Assign with instance reference

    art_no = StringBone(
        escape_html=False,
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

    delivery_time_range = StringBone(
        compute=Compute(lambda skel: (str(skel["delivery_time_min"])
                                      if skel["delivery_time_min"] == skel["delivery_time_max"]
                                      else f'{skel["delivery_time_min"]} - {skel["delivery_time_max"]}')),
        escape_html=False,
    )
