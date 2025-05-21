import typing as t  # noqa
from datetime import datetime as dt

from viur.core import conf, i18n
from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.types import *
from ..globals import SHOP_LOGGER
from ..modules.discount_condition import CODE_CHARS

logger = SHOP_LOGGER.getChild(__name__)


class DiscountConditionSkel(Skeleton):
    kindName = "{{viur_shop_modulename}}_discount_condition"

    interBoneValidations = [
        # Make individual_codes_amount required if selected as CodeType.INDIVIDUAL
        lambda skel: (
            [ReadFromClientError(
                ReadFromClientErrorSeverity.Invalid,
                "individual_codes_amount must be greater than 0",
                ["individual_codes_amount"],
                ["individual_codes_amount"],
            )]
            if skel["code_type"] == CodeType.INDIVIDUAL and not skel["individual_codes_amount"]
            else []
        ),
        # Make individual_codes_prefix required if selected as CodeType.INDIVIDUAL
        lambda skel: (
            [ReadFromClientError(
                ReadFromClientErrorSeverity.Invalid,
                "individual_codes_prefix must be not-empty",
                ["individual_codes_prefix"],
                ["individual_codes_prefix"],
            )]
            if skel["code_type"] == CodeType.INDIVIDUAL and not skel["individual_codes_prefix"]
            else []
        ),
    ]

    name = StringBone(
        compute=Compute(
            fn=lambda skel: str({
                key: "..." if key == "scope_article" else (value.isoformat() if isinstance(value, dt) else value)
                for key, value in skel.items(True)
                if value and value != getattr(skel, key).defaultValue and key not in dir(Skeleton)
            }),
            interval=ComputeInterval(
                method=ComputeMethod.OnWrite,
            ),
        ),
        params={
            "category": "1 – General",
        },
        escape_html=False,
        searchable=True,
    )

    description = TextBone(
        validHtml=None,
        params={
            "category": "1 – General",
        },
        searchable=True,
    )

    code_type = SelectBone(
        required=True,
        values=CodeType,
        defaultValue=CodeType.NONE,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={
            "category": "1 – General",
        },
    )

    application_domain = SelectBone(
        required=True,
        values=ApplicationDomain,
        defaultValue=ApplicationDomain.ALL,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={
            "category": "1 – General",
        },
    )
    """Anwendungsbereich"""

    quantity_volume = NumericBone(
        required=True,
        defaultValue=-1,  # Unlimited
        min=-1,
        getEmptyValueFunc=lambda: None,
        params={
            "category": "1 – General",
            "tooltip": "-1 ^= unlimited",
        },
    )

    quantity_used = NumericBone(
        defaultValue=0,
        min=0,
        params={
            "category": "1 – General",
        },
    )
    """Wie oft wurde der code Bereits verwendet?"""

    individual_codes_amount = NumericBone(
        min=1,
        params={
            "category": "1 – General",
            "visibleIf": 'code_type == "individual"'
        },
        defaultValue=0,
    )

    scope_code = StringBone(
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "universal"',
            "pattern": rf'^[{"".join(CODE_CHARS)}]+$',
            "tooltip": i18n.translate(
                "viur.shop.skeleton.discountcondition.scope_code.allowed_characters",
                defaultText="allowed characters: {{chars}}",
                default_variables=dict(chars="".join(CODE_CHARS))
            ),
        },
        vfunc=StringBone.v_func_valid_chars(f'{("".join(CODE_CHARS)).lower()}{("".join(CODE_CHARS)).upper()}'),
        unique=UniqueValue(UniqueLockMethod.SameValue, False, "Code exist already"),  # TODO
        escape_html=False,
        caseSensitive=False,
        searchable=True,
    )

    individual_codes_prefix = StringBone(
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "individual"',
            "pattern": rf'^[{"".join(CODE_CHARS)}]+$',
            "tooltip": i18n.translate(
                "viur.shop.skeleton.discountcondition.scope_code.allowed_characters",
                defaultText="allowed characters: {{chars}}",
                default_variables=dict(chars="".join(CODE_CHARS))
            ),
        },
        vfunc=StringBone.v_func_valid_chars(f'{("".join(CODE_CHARS)).lower()}{("".join(CODE_CHARS)).upper()}'),
        unique=UniqueValue(UniqueLockMethod.SameValue, False, "Value already taken"),
        escape_html=False,
        searchable=True,
    )

    scope_minimum_order_value = NumericBone(
        required=True,
        min=0,
        defaultValue=0,
        getEmptyValueFunc=lambda: None,
        # TODO: UnitBone / CurrencyBone
        params={
            "category": "2 – Scope",
        },
    )

    scope_date_start = DateBone(
        params={
            "category": "2 – Scope",
        },
    )

    scope_date_end = DateBone(
        params={
            "category": "2 – Scope",
        },
    )

    scope_language = SelectBone(
        values=conf.i18n.available_languages,
        params={
            "category": "2 – Scope",
        },
        multiple=True,
    )

    scope_country = SelectCountryBone(
        params={
            "category": "2 – Scope",
        },
        multiple=True,
    )

    scope_minimum_quantity = NumericBone(
        required=True,
        min=0,
        defaultValue=0,
        getEmptyValueFunc=lambda: None,
        params={
            "category": "2 – Scope",
        },
    )
    """Minimale Anzahl

    für Staffelrabatte (in Kombination mit application_domain) für Artikel oder kompletten Warenkorb"""

    scope_customer_group = SelectBone(
        required=True,
        values=CustomerGroup,
        defaultValue=CustomerGroup.ALL,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={
            "category": "2 – Scope",
        },
    )

    scope_combinable_other_discount = BooleanBone(
        params={
            "category": "2 – Scope",
        },
    )
    """Kombinierbar mit anderen Rabatten"""

    scope_combinable_low_price = BooleanBone(
        params={
            "category": "2 – Scope",
        },
    )
    """Kombinierbar

    prüfen mit shop_is_low_price"""

    scope_article = RelationalBone(
        kind="...",  # will be set in Shop._set_kind_names()
        consistency=RelationalConsistency.PreventDeletion,
        params={
            "category": "2 – Scope",
            "visibleIf": 'application_domain == "article"'
        },
        refKeys=["name", "shop_name", "shop_*"],
        format="$(dest.shop_name) | $(dest.shop_shop_art_no_or_gtin) | $(dest.shop_price_retail) €",
        multiple=True,
    )

    is_subcode = BooleanBone(
        compute=Compute(
            fn=lambda skel: skel["parent_code"] is not None,
            interval=ComputeInterval(
                method=ComputeMethod.OnWrite,
            ),
        ),
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "individual"'
        },
        readOnly=True,
    )

    parent_code = RelationalBone(
        kind="{{viur_shop_modulename}}_discount_condition",
        module="{{viur_shop_modulename}}/discount_condition",
        consistency=RelationalConsistency.PreventDeletion,
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "individual"'
        },
        readOnly=True,
    )
