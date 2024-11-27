import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import RelSkel

from ..types import VatRate
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class VatSkel(RelSkel):
    rate = SelectBone(
        values=VatRate,
        translation_key_prefix="viur.shop.vat_rate.",
        required=True,
    )

    value = NumericBone(
        required=True,
        precision=2,
        min=0,
        getEmptyValueFunc=lambda: None,
        # TODO: UnitBone / PercentageBone
    )
