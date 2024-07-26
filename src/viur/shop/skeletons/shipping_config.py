import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from .shipping_precondition import ShippingPreconditionRelSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ShippingConfigSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_shipping_config"

    name = StringBone(
    )

    shipping_skel = RelationalBone(
        kind="shop_shipping",
        module="shop/shipping",
        using=ShippingPreconditionRelSkel,
        consistency=RelationalConsistency.PreventDeletion,
        multiple=True,
    )
