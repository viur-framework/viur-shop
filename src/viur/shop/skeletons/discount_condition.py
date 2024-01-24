import logging

from viur.core import conf
from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.constants import *

logger = logging.getLogger("viur.shop").getChild(__name__)


class DiscountConditionSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_discount_condition"

    name = StringBone(
        descr="name",
        compute=Compute(
            fn=lambda skel: str({
                key: value
                for key, value in skel.items(True)
                if value is not None and key not in dir(Skeleton)
            }),
            interval=ComputeInterval(
                method=ComputeMethod.OnWrite,
            ),
        ),
        params={
            "category": "1 – General",
        },
    )

    description = TextBone(
        descr="description",
        validHtml=None,
        params={
            "category": "1 – General",
        },
    )

    code_type = SelectBone(
        descr="code_type",
        # required=True,
        values=CodeType,
        defaultValue=CodeType.NONE,
        params={
            "category": "1 – General",
        },
    )

    application_domain = SelectBone(
        descr="application_domain",
        required=True,
        values=ApplicationDomain,
        defaultValue=ApplicationDomain.BASKET,
        params={
            "category": "1 – General",
        },
    )
    """Anwendungsbereich"""

    quantity_volume = NumericBone(
        descr="quantity_volume",
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
        descr="quantity_used",
        defaultValue=0,
        min=0,
        params={
            "category": "1 – General",
        },
    )
    """Wie oft wurde der code Bereits verwendet?"""

    individual_codes_amount = NumericBone(
        descr="individual_codes_amount",
        min=1,
        params={
            "category": "1 – General",
            "visibleIf": 'code_type == "individual"'
        },
    )

    scope_code = StringBone(
        descr="code",
        # TODO: limit charset
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "universal"'
        },
    )

    individual_codes_prefix = StringBone(
        descr="individual_codes_prefix",
        # TODO: limit charset
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "individual"'
        },
    )

    scope_minimum_order_value = NumericBone(
        descr="scope_minimum_order_value",
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
        descr="scope_date_start",
        params={
            "category": "2 – Scope",
        },
    )

    scope_date_end = DateBone(
        descr="scope_date_end",
        params={
            "category": "2 – Scope",
        },
    )

    scope_language = SelectBone(
        descr="scope_language",
        values=conf.i18n.available_languages,
        params={
            "category": "2 – Scope",
        },
    )

    scope_country = SelectCountryBone(
        descr="scope_country",
        params={
            "category": "2 – Scope",
        },
    )

    scope_minimum_quantity = NumericBone(
        descr="scope_minimum_quantity",
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
        descr="scope_customer_group",
        required=True,
        values=CustomerGroup,
        defaultValue=CustomerGroup.ALL,
        params={
            "category": "2 – Scope",
        },
    )

    scope_combinable_other_discount = BooleanBone(
        descr="scope_combinable_other_discount",
        params={
            "category": "2 – Scope",
        },
    )
    """Kombinierbar mit anderen Rabatten"""

    scope_combinable_low_price = BooleanBone(
        descr="scope_combinable_low_price",
        params={
            "category": "2 – Scope",
        },
    )
    """Kombinierbar

    prüfen mit shop_is_low_price"""

    scope_article = RelationalBone(
        descr="scope_article",
        kind="...",  # will be set in Shop._set_kind_names()
        consistency=RelationalConsistency.PreventDeletion,
        params={
            "category": "2 – Scope",
            "visibleIf": 'application_domain == "article"'
        },
    )

    is_subcode = BooleanBone(
        descr="is_subcode",
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
    )

    parent_code = RelationalBone(
        descr="parent_code",
        kind="shop_discount_condition",
        module="shop.discount_condition",
        consistency=RelationalConsistency.PreventDeletion,
        params={
            "category": "2 – Scope",
            "visibleIf": 'code_type == "individual"'
        },
    )
