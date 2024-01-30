import logging

from viur.core import conf, db
from viur.core.bones import *
from viur.core.prototypes.tree import TreeSkel
from viur.core.skeleton import SkeletonInstance
from viur.shop.constants import *

logger = logging.getLogger("viur.shop").getChild(__name__)


class TotalFactory:
    def __init__(
        self,
        bone_node: str | t.Callable[["SkeletonInstance"], float | int],
        bone_leaf: str | t.Callable[["SkeletonInstance"], float | int],
        multiply_quantity: bool = True,
        precision: int | None = None,
        use_cache: bool = True,
    ):
        super().__init__()
        self.bone_node = bone_node
        self.bone_leaf = bone_leaf
        self.multiply_quantity = multiply_quantity
        self.precision = precision
        self.use_cache = use_cache

    def _get_children(self, parent_cart_key: db.Key) -> list[SkeletonInstance]:
        if self.use_cache:
            return conf.main_app.shop.cart.get_children_from_cache(parent_cart_key)
        else:
            return conf.main_app.shop.cart.get_children(parent_cart_key)

    def __call__(self, skel: "CartNodeSkel", bone: NumericBone):
        children = self._get_children(skel["key"])
        total = 0
        for child in children:
            # logger.debug(f"{child = }")
            if issubclass(child.skeletonCls, CartNodeSkel):
                if callable(self.bone_node):
                    total += self.bone_node(child)
                else:
                    total += child[self.bone_node]
            elif issubclass(child.skeletonCls, CartItemSkel):
                if callable(self.bone_leaf):
                    value = self.bone_leaf(child)
                else:
                    value = child[self.bone_leaf]
                if value:
                    if self.multiply_quantity:
                        value *= child["quantity"]
                    total += value
        return round(
            total,
            self.precision if self.precision is not None else bone.precision
        )


def get_vat_rate_for_node(skel: "CartNodeSkel", bone: RelationalBone):
    children = conf.main_app.shop.cart.get_children_from_cache(skel["key"])
    rel_keys = set()
    # logger.debug(f"{skel = }")
    for child in children:
        # logger.debug(f"{child = }")
        if issubclass(child.skeletonCls, CartNodeSkel):
            for rel in child["vat_rate"] or []:
                rel_keys.add(rel["dest"]["key"])
        elif issubclass(child.skeletonCls, CartItemSkel):
            if child["shop_vat"] is not None:
                rel_keys.add(child["shop_vat"]["dest"]["key"])
    return [
        bone.createRelSkelFromKey(key)
        for key in rel_keys
    ]


class CartNodeSkel(TreeSkel):  # STATE: Complete (as in model)
    kindName = "shop_cart_node"

    is_root_node = BooleanBone(
        descr="Is root node?",
        readOnly=True,
    )

    total = NumericBone(
        descr="Total",
        precision=2,
        compute=Compute(
            TotalFactory("total", "price_sale", True),
            ComputeInterval(ComputeMethod.Always),
        ),
    )

    vat_total = NumericBone(
        descr="Total",
        precision=2,
        compute=Compute(
            TotalFactory("vat_total", lambda child: child.shop_vat_value, True),
            ComputeInterval(ComputeMethod.Always),
        ),
    )

    vat_rate = RelationalBone(
        descr="Vat Rate",
        kind="shop_vat",
        module="shop/vat",
        compute=Compute(get_vat_rate_for_node, ComputeInterval(ComputeMethod.Always)),
        refKeys=["key", "name", "rate"],
        multiple=True,
    )

    total_quantity = NumericBone(
        descr="Total quantity",
        precision=0,
        compute=Compute(
            TotalFactory("total_quantity", lambda child: 1, True),
            ComputeInterval(ComputeMethod.Always)
        ),
        defaultValue=0,
    )

    shipping_address = RelationalBone(
        descr="shipping_address",
        kind="shop_address",
        module="shop/shop_address",
        refKeys=[
            "key", "name", "customer_type", "salutation", "company_name",
            "firstname", "lastname", "street_name", "street_number",
            "address_addition", "zip_code", "city", "country",
            "is_default", "address_type",
        ],
    )

    customer_comment = TextBone(
        descr="customer_comment",
        validHtml=None,
    )

    name = StringBone(
        descr="name",
    )

    cart_type = SelectBone(
        descr="cart_type",
        values=CartType,
    )

    shipping = RelationalBone(
        descr="shipping",
        kind="shop_shipping",
        module="shop/shipping",
    )
    """Versand bei Warenkorb der einer Bestellung zugehört"""

    discount = RelationalBone(
        descr="discount",
        kind="shop_discount",
        module="shop/discount",
        refKeys=["key", "name", "discount_type", "absolute", "percentage"],
    )


class CartItemSkel(TreeSkel):  # STATE: Complete (as in model)
    kindName = "shop_cart_leaf"

    article = RelationalBone(
        descr="article",
        kind="...",  # will be set in Shop._set_kind_names()
        # FIXME: What's necessary here?
        parentKeys=["key", "parententry", "article"],
        refKeys=[
            "shop_name", "shop_description",
            "shop_price_retail", "shop_price_recommended",
            "shop_availability", "shop_listed",
            "shop_image", "shop_art_no_or_gtin",
            "shop_vat", "shop_shipping",
            "shop_is_weee", "shop_is_low_price",
            "shop_price_current",
        ],
        consistency=RelationalConsistency.CascadeDeletion,
    )

    quantity = NumericBone(
        descr="quantity",
        min=0,
        defaultValue=0,
    )

    project_data = JsonBone(
        descr="Custom project data",
    )

    # --- Bones to store a frozen copy of the article values: -----------------

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
        module="shop.vat",
        refKeys=["key", "name", "rate"],
        consistency=RelationalConsistency.PreventDeletion,
    )

    shop_shipping = RelationalBone(
        descr="Versandkosten",
        kind="shop_shipping_config",
        module="shop.shipping_config",
        consistency=RelationalConsistency.SetNull,
    )

    shop_is_weee = BooleanBone(
        descr="Elektro",
    )

    shop_is_low_price = BooleanBone(
        descr="shop_is_low_price",
    )

    @property
    def shop_vat_value(self):
        """Calculate the vat value based on price and vat rate"""
        if not (vat := self["shop_vat"]):
            return 0
        return (vat["dest"]["rate"] or 0) / 100 * self["price_sale"]

    @property
    def article_skel(self):
        return self["article"]["dest"]

    @property
    def parent_skel(self):
        if not (pk := self["parententry"]):
            return None
        from viur.shop.shop import SHOP_INSTANCE
        skel = SHOP_INSTANCE.get().cart.viewSkel("node")
        assert skel.fromDB(pk)
        return skel

    @property
    def price_sale_(self):
        # TODO: where to store methods like this?
        article_price = self.article_skel["shop_price_current"]
        if discount := (self.parent_skel["discount"]):
            # At this point we can make sure the discount is valid applied
            # -- even if the article is already discounted
            discount = discount["dest"]
            # logger.debug(f'{self=} // {discount=} // {self.parent_skel=}')
            if discount["discount_type"] == DiscountType.FREE_ARTICLE:
                return 0
            elif discount["discount_type"] == DiscountType.ABSOLUTE:
                return article_price - discount["absolute"]
            elif discount["discount_type"] == DiscountType.PERCENTAGE:
                return article_price - (
                    article_price * discount["percentage"] / 100
                )
            else:
                raise NotImplementedError(discount["discount_type"])
        return article_price

    price_sale = NumericBone(
        descr="sale_price_bone",
        compute=Compute(lambda skel: skel.price_sale_, ComputeInterval(ComputeMethod.Always))
    )

    @classmethod
    def toDB(cls, skelValues: SkeletonInstance, update_relations: bool = True, **kwargs) -> db.Key:
        return super().toDB(skelValues, update_relations, **kwargs)
