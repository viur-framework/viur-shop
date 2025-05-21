import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton, SkeletonInstance
from .shipping_precondition import ShippingPreconditionRelSkel
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class ShippingConfigSkel(Skeleton):
    kindName = "{{viur_shop_modulename}}_shipping_config"

    name = StringBone(
        searchable=True,
        escape_html=False,
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
            "art_no",
            "delivery_time_*",
        },
        searchable=True,
    )

    @classmethod
    def read(cls, skel: SkeletonInstance, *args, **kwargs) -> bool:
        # Migration after renaming
        res = super().read(skel, *args, **kwargs)
        if not skel.dbEntity.get("shipping"):
            skel.dbEntity["shipping"] = skel.dbEntity.get("shipping_skel")
        return res
