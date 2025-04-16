import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from .vat import VatSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class VatRateSkel(Skeleton):
    kindName = "{{viur_shop_modulename}}_vat_rate"

    name = StringBone(
        compute=Compute(
            lambda skel: ' | '.join((
                f'{skel["country"]}',
                ", ".join(f'{v["category"]}: {v["percentage"]} %' for v in skel["configuration"]),
            )),
            ComputeInterval(ComputeMethod.OnWrite)
        ),
        escape_html=False,
        searchable=True,
    )

    country = SelectCountryBone(
        required=True,
        unique=UniqueValue(UniqueLockMethod.SameValue, False, "Value already taken"),
    )

    configuration = RecordBone(
        using=VatSkel,
        required=True,
        multiple=True,
        format="$(dest.category): $(dest.percentage) %",
    )
