import abc

from viur.core.bones import *
from viur.core.prototypes.tree import TreeSkel

import logging

from viur.core.skeleton import Skeleton

logger = logging.getLogger("viur.shop").getChild(__name__)


class VatSkel(Skeleton):
    kindName = "shop_vat"

    rate = NumericBone(
        descr="Rate",
    )

