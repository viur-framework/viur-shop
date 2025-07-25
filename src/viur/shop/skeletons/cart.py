import collections
import typing as t  # noqa

from viur import toolkit
from viur.core import current, db, utils
from viur.core.bones import *
from viur.core.prototypes.tree import TreeSkel
from viur.core.skeleton import SkeletonInstance
from viur.shop.types import *
from .vat import VatIncludedSkel
from ..globals import SHOP_INSTANCE, SHOP_LOGGER
from ..skeletons.article import ArticleAbstractSkel
from ..types.response import make_json_dumpable

logger = SHOP_LOGGER.getChild(__name__)

Addition = t.Callable[["TotalFactory", float, SkeletonInstance_T["CartNodeSkel"], BaseBone], float]


class TotalFactory:
    def __init__(
        self,
        bone_node: str | t.Callable[[SkeletonInstance], float | int],
        bone_leaf: str | t.Callable[[SkeletonInstance], float | int],
        multiply_quantity: bool = True,
        precision: int | None = None,
        use_cache: bool = True,
        *,
        additions: list[Addition] | tuple[Addition, ...] = (),
    ):
        super().__init__()
        self.bone_node = bone_node
        self.bone_leaf = bone_leaf
        self.multiply_quantity = multiply_quantity
        self.precision = precision
        self.use_cache = use_cache
        self.additions = additions

    def _get_children(self, parent_cart_key: db.Key) -> list[SkeletonInstance]:
        if self.use_cache:
            return SHOP_INSTANCE.get().cart.get_children_from_cache(parent_cart_key)
        else:
            return SHOP_INSTANCE.get().cart.get_children(parent_cart_key)

    def __call__(self, skel: SkeletonInstance_T["CartNodeSkel"], bone: NumericBone):
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

        for addition in self.additions:
            total = addition(self, total, skel, bone)

        return round(
            total,
            self.precision if self.precision is not None else bone.precision
        )


# @toolkit.debug
def add_discount(factory: TotalFactory, total: float, skel: "SkeletonInstance", bone: BaseBone) -> float:
    if discount := skel["discount"]:
        if any(
            condition["dest"]["application_domain"] == ApplicationDomain.BASKET
            for condition in discount["dest"]["condition"]
        ):
            total = Price.apply_discount(discount["dest"], total)
    return total


# @toolkit.debug
def add_shipping(factory: TotalFactory, total: float, skel: "SkeletonInstance", bone: BaseBone) -> float:
    if shipping := skel["shipping"]:
        total += shipping["dest"]["shipping_cost"] or 0.0
    return total


def get_vat_for_node(skel: "CartNodeSkel", bone: RecordBone) -> list[dict]:
    children = SHOP_INSTANCE.get().cart.get_children_from_cache(skel["key"])
    cat2value = collections.defaultdict(lambda: 0)
    cat2rate = {}
    # logger.debug(f"{skel=}")
    for child in children:
        # logger.debug(f"{child=}")
        if issubclass(child.skeletonCls, CartNodeSkel):
            for entry in child["vat"] or []:
                # logger.debug(f'{child["shop_vat_rate_category"]} | {entry=}')
                cat2value[entry["category"]] += entry["value"]
                cat2rate[entry["category"]] = entry["percentage"]
        elif issubclass(child.skeletonCls, CartItemSkel):
            try:
                cat2value[child["shop_vat_rate_category"]] += child.price_.vat_included * child["quantity"]
                cat2rate[child["shop_vat_rate_category"]] = child.price_.vat_rate_percentage
            except TypeError as e:
                logger.warning(e)

    if shipping := skel["shipping"]:
        try:
            shipping_country = skel["shipping_address"]["dest"]["country"]
        except (KeyError, TypeError):
            shipping_country = None
        vat_percentage = SHOP_INSTANCE.get().vat_rate.get_vat_rate_for_country(
            country=shipping_country, category=VatRateCategory.STANDARD,
        )
        vat_value = Price.gross_to_vat(shipping["dest"]["shipping_cost"] or 0.0, vat_percentage / 100.0)
        cat2rate[VatRateCategory.STANDARD] = vat_percentage / 100.0
        cat2value[VatRateCategory.STANDARD] += vat_value

    return [
        {
            "category": cat,
            "value": toolkit.round_decimal(value, bone.using.percentage.precision),
            "percentage": cat2rate[cat],
        }
        for cat, value in cat2value.items()
        if cat and value
    ]


class RelationalBoneShipping(RelationalBone):
    """A custom RelationalBone with conditionally compute logic for shipping"""

    def unserialize_compute(self, skel: "SkeletonInstance", name: str) -> bool:
        """
        This method implements a conditionally compute.

        Depending on the value of the 'shipping_status' bone, the cheapest
        shipping option will be calculated. Otherwise, the shipping method
        chosen by the user will be unserialized as usual.
        """
        assert name == "shipping", f"Special bone is only for shipping, but not for {name=}"
        # logger.debug(f"{skel["shipping_status"]=}")

        if getattr(self, "_prevent_compute", False):  # avoid recursion errors
            return False

        if skel["shipping_status"] == ShippingStatus.USER and self._is_valid_user_shipping(skel):
            return False  # should be unserialized from entity

        if skel["is_frozen"]:  # locked, unserialize the latest stored value from entity
            return False

        match skel["shipping_status"]:
            case ShippingStatus.CHEAPEST:
                func = min
            case ShippingStatus.MOST_EXPENSIVE:
                func = max
            case _:
                func = None

        if func is not None:  # compute cheapest & most expensive
            self._prevent_compute = True
            try:
                applicable_shippings = SHOP_INSTANCE.get().shipping.get_shipping_skels_for_cart(
                    cart_skel=skel, use_cache=True,
                )
                if applicable_shippings:
                    cheapest_shipping = func(applicable_shippings,
                                             key=lambda shipping: shipping["dest"]["shipping_cost"] or 0)
                    skel.setBoneValue("shipping", cheapest_shipping["dest"]["key"])
            finally:
                self._prevent_compute = False

            return True

        return super().unserialize_compute(skel, name)

    def _is_valid_user_shipping(self, skel: SkeletonInstance) -> bool:
        """Ensure it's still a valid shipping for the cart"""
        try:
            shipping_key = skel.dbEntity["shipping"]["dest"].key
        except (KeyError, TypeError, AttributeError):
            shipping_key = None
        if shipping_key is None:
            return True
        self._prevent_compute = True
        try:
            applicable_shippings = SHOP_INSTANCE.get().shipping.get_shipping_skels_for_cart(
                cart_skel=skel, use_cache=True,
            )
            for shipping in applicable_shippings:
                if shipping["dest"]["key"] == shipping_key:
                    return True
            else:
                logger.warning(f"Invalid shipping. {shipping_key=!r} not found in applicable_shippings")
                skel.setBoneValue("shipping", None)
                skel.setBoneValue("shipping_status", skel.shipping_status.getDefaultValue(skel))
                return False
        finally:
            self._prevent_compute = False


class CartNodeSkel(TreeSkel):
    kindName = "{{viur_shop_modulename}}_cart_node"

    subSkels = {
        "discount": ["key", "discount", "parententry"],  # for modules.cart.get_discount_for_leaf
    }

    is_root_node = BooleanBone(
        readOnly=True,
    )

    total = NumericBone(
        precision=2,
        compute=Compute(
            TotalFactory("total", lambda child: child.price_.current, True,
                         additions=[add_shipping]),
            ComputeInterval(ComputeMethod.Always),
        ),
    )

    total_raw = NumericBone(
        precision=2,
        compute=Compute(
            TotalFactory("total", lambda child: child.price_.current, True),
            ComputeInterval(ComputeMethod.Always),
        ),
    )

    total_discount_price = NumericBone(
        precision=2,
        compute=Compute(
            TotalFactory("total_discount_price", lambda child: child.price_.current, True,
                         additions=[add_discount, add_shipping]),
            ComputeInterval(ComputeMethod.Always),
        ),
    )

    vat = RecordBone(
        using=VatIncludedSkel,
        multiple=True,
        format="$(dest.category) ($(dest.percentage)) : $(dest.value)",
        compute=Compute(
            get_vat_for_node,
            ComputeInterval(ComputeMethod.Always),
        ),
    )

    total_quantity = NumericBone(
        precision=0,
        compute=Compute(
            TotalFactory("total_quantity", lambda child: 1, True),
            ComputeInterval(ComputeMethod.Always)
        ),
        defaultValue=0,
    )

    shipping_address = RelationalBone(
        kind="{{viur_shop_modulename}}_address",
        module="{{viur_shop_modulename}}/address",
        refKeys=[
            "key", "name", "customer_type", "salutation", "company_name",
            "firstname", "lastname", "street_name", "street_number",
            "address_addition", "zip_code", "city", "country",
            "email", "phone",
            "is_default", "address_type",
        ],
    )

    customer_comment = TextBone(
        validHtml=None,
        searchable=True,
    )

    name = StringBone(
        defaultValue=lambda skel, bone: (
            f'Session Cart of {current.user.get() and current.user.get()["name"] or "__guest__"}'
            f' created at {utils.utcNow()}'
        ),
        searchable=True,
        escape_html=False,
    )

    cart_type = SelectBone(
        values=CartType,
        translation_key_prefix=None,
    )

    shipping = RelationalBoneShipping(
        kind="{{viur_shop_modulename}}_shipping",
        module="{{viur_shop_modulename}}/shipping",
        refKeys=[
            "name",
            "description",
            "shipping_cost",
            "supplier",
            "delivery_time_range",
        ],
    )
    shipping_status = SelectBone(
        values=ShippingStatus,
        defaultValue=ShippingStatus.CHEAPEST
    )
    """Versand bei Warenkorb der einer Bestellung zugehört"""

    discount = RelationalBone(
        kind="{{viur_shop_modulename}}_discount",
        module="{{viur_shop_modulename}}/discount",
        refKeys=[
            "key",
            "name",
            "discount_type",
            "absolute",
            "percentage",
            "condition"
        ],
    )

    project_data = JsonBone(
    )

    is_frozen = BooleanBone(
        readOnly=True,
        defaultValue=False,
    )

    frozen_values = JsonBone(
        readOnly=True,
        visible=False,
    )

    @classmethod
    def refresh_shipping_address(cls, skel: SkeletonInstance) -> SkeletonInstance:
        """
        Shorthand to refresh the shipping_address of an CartNodeSkel
        Due to race-condition and timing issues, the dest values are not always
        set correctly. This refresh fixes this.
        """
        try:
            skel.shipping_address.refresh(skel, skel.shipping_address.name)
        except Exception as exc:
            logger.debug(f'Failed to refresh shipping_address on cart {skel["key"]!r}: {exc}')
        return skel

    @classmethod
    def read(cls, skel: SkeletonInstance, *args, **kwargs) -> t.Optional[SkeletonInstance]:
        if res := super().read(skel, *args, **kwargs):
            cls.refresh_shipping_address(skel)
        return res


class CartItemSkel(TreeSkel):
    kindName = "{{viur_shop_modulename}}_cart_leaf"

    article = RelationalBone(
        kind="...",  # will be set in Shop._set_kind_names()
        module="...",  # will be set in Shop._set_kind_names()
        parentKeys=["key", "parententry", "article"],
        refKeys=[
            "shop_*",
        ],
        consistency=RelationalConsistency.CascadeDeletion,
    )

    quantity = NumericBone(
        min=0,
        defaultValue=0,
    )

    project_data = JsonBone(
    )

    # --- Bones to store a frozen copy of the article values: -----------------

    shop_name = StringBone(
        searchable=True,
        escape_html=False,
    )

    shop_description = TextBone(
    )

    shop_price_retail = NumericBone(
    )

    shop_price_recommended = NumericBone(
    )

    shop_availability = SelectBone(
        values=ArticleAvailability,
        translation_key_prefix=None,
    )

    shop_listed = BooleanBone(
    )

    shop_image = FileBone(
    )

    shop_art_no_or_gtin = StringBone(
        escape_html=False,
    )

    shop_vat_rate_category = SelectBone(
        values=VatRateCategory,
        translation_key_prefix="viur.shop.vat_rate_category.",
    )

    shop_shipping_config = RelationalBone(
        kind="{{viur_shop_modulename}}_shipping_config",
        module="{{viur_shop_modulename}}/shipping_config",
        consistency=RelationalConsistency.SetNull,
    )

    shop_is_weee = BooleanBone(
    )

    shop_is_low_price = BooleanBone(
    )

    @property
    def article_skel(self) -> SkeletonInstance:
        return self["article"]["dest"]

    @property
    def article_skel_full(self) -> SkeletonInstance_T[ArticleAbstractSkel]:
        # logger.debug(f'Access article_skel_full {self.article_skel["key"]=}')
        try:
            return CartItemSkel.get_article_cache()[self.article_skel["key"]]
        except KeyError:
            # logger.debug(f'Read article_skel_full {self.article_skel["key"]=}')
            skel = SHOP_INSTANCE.get().article_skel()
            assert skel.read(self.article_skel["key"])
            CartItemSkel.get_article_cache()[self.article_skel["key"]] = skel
            return skel

    @classmethod
    def get_article_cache(cls) -> dict[db.Key, SkeletonInstance_T[ArticleAbstractSkel]]:
        if current.request_data.get() is None:
            return {}
        return (
            current.request_data.get().setdefault("viur.shop", {})
            .setdefault("article_cache", {})
        )

    @property
    def parent_skel(self) -> SkeletonInstance:
        if not (pk := self["parententry"]):
            return None
        skel = SHOP_INSTANCE.get().cart.viewSkel("node")
        assert skel.read(pk)
        return skel

    @property
    def price_(self) -> Price:
        return Price.get_or_create(self)

    price = JsonBone(
        compute=Compute(lambda skel: skel.price_.to_dict(), ComputeInterval(ComputeMethod.Always))
    )

    shipping = JsonBone(
        compute=Compute(
            lambda skel: make_json_dumpable(
                SHOP_INSTANCE.get().shipping.choose_shipping_skel_for_article(skel.article_skel_full)
            ),
            ComputeInterval(ComputeMethod.Always)),
    )

    is_frozen = BooleanBone(
        readOnly=True,
        defaultValue=False,
    )

    frozen_values = JsonBone(
        readOnly=True,
        visible=False,
    )
