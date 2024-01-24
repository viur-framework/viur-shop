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
        params={
            "visibleIf": 'discount_type == "absolute"',
            "requiredIf": 'discount_type == "absolute"',
        },
    )

    percentage = NumericBone(
        descr="percentage",
        precision=2,
        min=0,
        max=100,
        # TODO: UnitBone / PercentageBone
        params={
            "visibleIf": 'discount_type == "percentage"',
            "requiredIf": 'discount_type == "percentage"',
        },
    )

    free_article = RelationalBone(
        descr="free_article",
        kind="...",  # will be set in Shop._set_kind_names()
        params={
            "visibleIf": 'discount_type == "free_article"',
            "requiredIf": 'discount_type == "free_article"',
        },
    )

    condition = RelationalBone(
        descr="condition",
        kind="shop_discount_condition",
        module="shop.discount_condition",
        multiple=True,
        refKeys=["key", "name", "scope_code"],
        consistency=RelationalConsistency.PreventDeletion,
    )

    condition_operator = SelectBone(
        descr="condition_operator",
        required=True,
        values=ConditionOperator,
        defaultValue=ConditionOperator.ALL,
    )
