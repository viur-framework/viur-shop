import logging

from viur.core import conf
from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.constants import *

logger = logging.getLogger("viur.shop").getChild(__name__)


class DiscountConditionSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_discount_condition"

    code_type = SelectBone(
        descr="code_type",
        values=CodeType,
    )

    application_domain = SelectBone(
        descr="application_domain",
        values=ApplicationDomain,
    )
    """Anwendungsbereich"""

    quantity_volume = NumericBone(
        descr="quantity_volume",
        defaultValue=-1,  # Unlimited
        min=-1,
    )

    quantity_used = NumericBone(
        descr="quantity_used",
        defaultValue=0,
        min=0,
    )
    """Wie oft wurde der code Bereits verwendet?"""

    individual_codes_amount = NumericBone(
        descr="individual_codes_amount",
        min=1,
    )

    scope_code = StringBone(
        descr="code",
        # TODO: limit charset
    )

    individual_codes_prefix = StringBone(
        descr="individual_codes_prefix",
        # TODO: limit charset
    )

    scope_minimum_order_value = NumericBone(
        descr="scope_minimum_order_value",
        min=0,
        # TODO: UnitBone / CurrencyBone
    )

    scope_date_start = DateBone(
        descr="scope_date_start",
    )

    scope_date_end = DateBone(
        descr="scope_date_end",
    )

    scope_language = SelectBone(
        descr="scope_language",
        values=conf.i18n.available_languages,
    )

    scope_country = SelectCountryBone(
        descr="scope_country",
    )

    scope_minimum_quantity = NumericBone(
        descr="scope_minimum_quantity",
        min=0,
    )
    """Minimale Anzahl

    für Staffelrabatte (in Kombination mit application_domain) für Artikel oder kompletten Warenkorb"""

    scope_customer_group = SelectBone(
        descr="scope_customer_group",
        values=CustomerGroup,
    )

    scope_combinable_other_discount = BooleanBone(
        descr="scope_combinable_other_discount",
    )
    """Kombinierbar mit anderen Rabatten"""

    scope_combinable_low_price = BooleanBone(
        descr="scope_combinable_low_price",
    )
    """Kombinierbar

    prüfen mit shop_is_low_price"""

    scope_article = RelationalBone(
        descr="scope_article",
        kind="...",  # will be set in Shop._set_kind_names()
    )

    is_subcode = BooleanBone(
        descr="is_subcode",
        compute=Compute(
            fn=lambda skel: skel["parent_code"] is not None,
            interval=ComputeInterval(
                method=ComputeMethod.OnWrite,
            ),
        ),
    )

    parent_code = RelationalBone(
        descr="parent_code",
        kind="shop_discount_condition",
    )
