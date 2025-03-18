import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import RelSkel
from ..globals import SHOP_LOGGER
from ..types import VatRateCategory

logger = SHOP_LOGGER.getChild(__name__)


class VatSkel(RelSkel):
    category = SelectBone(
        values=VatRateCategory,
        translation_key_prefix="viur.shop.vat_rate_category.",
        required=True,
    )

    percentage = NumericBone(
        required=True,
        precision=2,
        min=0,
        getEmptyValueFunc=lambda: None,
        # TODO: UnitBone / PercentageBone
    )
    """Vat rate (percentage)"""


class VatIncludedSkel(VatSkel):
    value = NumericBone(
        required=True,
        precision=2,
        min=0,
        getEmptyValueFunc=lambda: None,
        # TODO: UnitBone / CurrencyBone
    )
    """Included vat value (EUR)"""
