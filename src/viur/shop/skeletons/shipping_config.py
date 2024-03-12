import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from .shipping_precondition import ShippingPreconditionRelSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ShippingConfigSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_shipping_config"

    name = StringBone(
        descr="name",
    )

    shipping_skel = RelationalBone(
        descr="shipping_skel",
        kind="shop_shipping",
        module="shop.shipping",
        using=ShippingPreconditionRelSkel,
        multiple=True,
    )
