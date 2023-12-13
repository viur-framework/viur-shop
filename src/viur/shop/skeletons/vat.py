import logging

from viur.core.bones import *
from viur.core.skeleton import Skeleton

logger = logging.getLogger("viur.shop").getChild(__name__)


class VatSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_vat"

    rate = NumericBone(
        descr="rate",
        precision=2,
        min=0,
    )
