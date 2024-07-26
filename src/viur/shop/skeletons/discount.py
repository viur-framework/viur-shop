import typing as t  # noqa

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.types import *
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class DiscountSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_discount"

    interBoneValidations = [
        # Make percentage required if selected as discount_type
        lambda skel: (
            [ReadFromClientError(
                ReadFromClientErrorSeverity.Invalid,
                "Percentage must be greater than 0",
                ["percentage"],
                ["percentage"],
            )]
            if skel["discount_type"] == DiscountType.PERCENTAGE and not skel["percentage"]
            else []
        ),
        # Make absolute required if selected as discount_type
        lambda skel: (
            [ReadFromClientError(
                ReadFromClientErrorSeverity.Invalid,
                "Absolute must be greater than 0",
                ["absolute"],
                ["absolute"],
            )]
            if skel["discount_type"] == DiscountType.ABSOLUTE and not skel["absolute"]
            else []
        ),
        # ApplicationDomain must be the same
        lambda skel: (
            [ReadFromClientError(
                ReadFromClientErrorSeverity.Invalid,
                "ApplicationDomains of all conditions must be basket or article, not mixed",
                ["condition"],
                ["condition"],
            )]
            if len({condition["dest"]["application_domain"] for condition in skel["condition"]
                    if condition["dest"]["application_domain"] != ApplicationDomain.ALL}) > 1
            else []
        ),
        # ApplicationDomain must be the same
        lambda skel: (
            [ReadFromClientError(
                ReadFromClientErrorSeverity.Invalid,
                "ApplicationDomains not set in any condition",
                ["condition"],
                ["condition"],
            )]
            if len({condition["dest"]["application_domain"] for condition in skel["condition"]
                    if condition["dest"]["application_domain"] != ApplicationDomain.ALL}) == 0
            else []
        ),
    ]

    name = StringBone(
    )

    description = TextBone(
        validHtml=None,
    )

    discount_type = SelectBone(
        required=True,
        values=DiscountType,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
    )

    absolute = NumericBone(
        precision=2,
        min=0,
        # TODO: UnitBone / CurrencyBone
        params={
            "visibleIf": 'discount_type == "absolute"',
            "requiredIf": 'discount_type == "absolute"',
        },
    )

    percentage = NumericBone(
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
        kind="...",  # will be set in Shop._set_kind_names()
        params={
            "visibleIf": 'discount_type == "free_article"',
            "requiredIf": 'discount_type == "free_article"',
        },
        consistency=RelationalConsistency.PreventDeletion,
    )

    condition = RelationalBone(
        kind="shop_discount_condition",
        module="shop/discount_condition",
        multiple=True,
        refKeys=["key", "name", "scope_code", "application_domain"],
        consistency=RelationalConsistency.PreventDeletion,
    )

    condition_operator = SelectBone(
        required=True,
        values=ConditionOperator,
        defaultValue=ConditionOperator.ALL,
    )

    activate_automatically = BooleanBone(
    )
