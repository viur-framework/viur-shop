import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class VatSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "{{viur_shop_modulename}}_vat"

    # TODO: add descr bone?!

    name = StringBone(
        compute=Compute(lambda skel: f'{skel["rate"]} %', ComputeInterval(ComputeMethod.OnWrite)),
    )

    rate = NumericBone(
        required=True,
        precision=2,
        min=0,
        getEmptyValueFunc=lambda: None,
        # TODO: UnitBone / PercentageBone
    )
