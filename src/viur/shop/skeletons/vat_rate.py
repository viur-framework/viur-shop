import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton

from .vat import VatSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class VatRateSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "{{viur_shop_modulename}}_vat_rate"

    # TODO: add descr bone?!

    name = StringBone(
        compute=Compute(
            lambda skel: f'{skel["country"]} | {", ".join(": ".join(map(str, (v["rate"], v["value"]))) for v in skel["configuration"])}',
            ComputeInterval(ComputeMethod.OnWrite)
        ),
    )

    country = SelectCountryBone(
        required=True,
        unique=UniqueValue(UniqueLockMethod.SameValue, False, "Value already taken"),
    )

    configuration = RecordBone(
        using=VatSkel,
        required=True,
        multiple=True,
        format="$(rate): $(value)",
    )
