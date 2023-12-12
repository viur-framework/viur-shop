import logging

from viur.core.bones import *
from viur.core.prototypes.tree import TreeSkel
from viur.shop.constants import ArticleAvailability

logger = logging.getLogger("viur.shop").getChild(__name__)


class CartNodeSkel(TreeSkel):  # STATE: partial (as in model)
    kindName = "shop_cart_node"

    total = NumericBone(
        descr="Total",
    )

    vat_total = NumericBone(
        descr="Total",
    )

    vat_rate = RelationalBone(
        descr="Vat Rate",
        kind="shop_vat",
    )


class CartItemSkel(TreeSkel):  # STATE: Complete (as in model)
    kindName = "shop_cart_leaf"

    article = RelationalBone(
        descr="article",
        kind="...",  # will be set in Shop._set_kind_names()
    )

    project_data = JsonBone(
        descr="Custom project data",
    )

    # Bones to store a frozen copy of the article values:

    shop_name = StringBone(
        descr="shop_name",
    )

    shop_description = TextBone(
        descr="shop_description",
    )

    shop_price_retail = NumericBone(
        descr="Verkaufspreis",
    )

    shop_price_recommended = NumericBone(
        descr="UVP",
    )

    shop_availability = SelectBone(
        descr="shop_availability",
        values=ArticleAvailability,
    )

    shop_listed = BooleanBone(
        descr="shop_listed",
    )

    shop_image = FileBone(
        descr="Produktbild",
    )

    shop_art_no_or_gtin = StringBone(
        descr="Artikelnummer",
    )

    shop_vat = RelationalBone(
        descr="Steuersatz",
        kind="shop_vat",
    )

    shop_shipping = RelationalBone(
        descr="Versandkosten",
        kind="shop_shipping",
    )

    shop_is_weee = BooleanBone(
        descr="Elektro",
    )

    shop_is_low_price = BooleanBone(
        descr="shop_is_low_price",
    )
