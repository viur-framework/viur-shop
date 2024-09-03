import typing as t  # noqa

from viur.core import db
from viur.core.bones import *
from viur.core.skeleton import Skeleton, SkeletonInstance
from .shipping_precondition import ShippingPreconditionRelSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ShippingConfigSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "{{viur_shop_modulename}}_shipping_config"

    name = StringBone(
    )

    shipping = RelationalBone(
        kind="{{viur_shop_modulename}}_shipping",
        module="{{viur_shop_modulename}}/shipping",
        using=ShippingPreconditionRelSkel,
        consistency=RelationalConsistency.PreventDeletion,
        multiple=True,
        refKeys={
            "name",
            "description",
            "supplier",
            "shipping_cost",
            "delivery_time_*",
        },
    )

    @classmethod
    def fromDB(cls, skel: SkeletonInstance, key: db.Key | int | str) -> bool:
        # Migration after renaming
        res = super().fromDB(skel, key)
        if not skel.dbEntity.get("shipping"):
            skel.dbEntity["shipping"] = skel.dbEntity.get("shipping_skel")
        return res
