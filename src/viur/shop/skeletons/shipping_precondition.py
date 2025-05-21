import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import RelSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ShippingPreconditionRelSkel(RelSkel):
    minimum_order_value = NumericBone(
        precision=2,
        min=0,
    )

    country = SelectCountryBone(
        multiple=True,
    )

    zip_code = StringBone(
        multiple=True,
        escape_html=False,
    )
