import logging

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.constants import *

logger = logging.getLogger("viur.shop").getChild(__name__)


class DiscountSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_discount"

    name = StringBone(
        descr="name",
    )

    description = TextBone(
        descr="description",
        validHtml=None,
    )

    discount_type = SelectBone(
        descr="discount_type",
        values=DiscountType,
    )

    absolute = NumericBone(
        descr="absolute",
        precision=2,
        min=0,
        # TODO: UnitBone / CurrencyBone
    )

    percentage = NumericBone(
        descr="percentage",
        precision=2,
        min=0,
        max=100,
        # TODO: UnitBone / PercentageBone
    )

    condition = RelationalBone(
        descr="condition",
        kind="shop_discount_condition",
    )

    condition_operator = SelectBone(
        descr="condition_operator",
        values=ConditionOperator,
    )
