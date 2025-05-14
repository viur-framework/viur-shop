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

    def unserialize_compute(self, skel: "SkeletonInstance", name: str) -> bool:
        """
        This function checks whether a bone is computed and if this is the case, it attempts to deserialise the
        value with the appropriate calculation method

        :param skel : The SkeletonInstance where the current Bone is located
        :param name: The name of the Bone in the Skeleton
        :return: True if the Bone was unserialized, False otherwise
        """
        assert name == "shipping", f"Special bone is only for shipping, but not for {name=}"

        logger.debug(f"{skel["shipping_status"]=}")

        if getattr(self, "_prevent_compute", False):
            return False

        if skel["shipping_status"] == ShippingStatus.USER:
            return False

        if skel["shipping_status"] == ShippingStatus.CHEAPEST:
            # if (
            #     and skel["key"] is not None  # During add there is no key assigned yet
            # ):
            self._prevent_compute = True
            with toolkit.TimeMe(f"shipping_status cheapest @ {skel["key"]!r} @ {current.request.get().path}"):
                applicable_shippings = SHOP_INSTANCE.get().shipping.get_shipping_skels_for_cart(cart_skel=skel,
                                                                                                use_cache=True)
                if applicable_shippings:
                    cheapest_shipping = min(applicable_shippings,
                                            key=lambda shipping: shipping["dest"]["shipping_cost"] or 0)
                    skel.setBoneValue("shipping", cheapest_shipping["dest"]["key"])
            self._prevent_compute = False

            return True

        if not self.compute or self._prevent_compute:
            return False

        match self.compute.interval.method:
            # Computation is bound to a lifetime?
            case ComputeMethod.Lifetime:
                now = utils.utcNow()
                from viur.core.skeleton import RefSkel  # noqa: E402 # import works only here because circular imports

                if issubclass(skel.skeletonCls, RefSkel):  # we have a ref skel we must load the complete Entity
                    db_obj = db.Get(skel["key"])
                    last_update = db_obj.get(f"_viur_compute_{name}_")
                else:
                    last_update = skel.dbEntity.get(f"_viur_compute_{name}_")
                    skel.accessedValues[f"_viur_compute_{name}_"] = last_update or now

                if not last_update or last_update + self.compute.interval.lifetime <= now:
                    # if so, recompute and refresh updated value
                    skel.accessedValues[name] = value = self._compute(skel, name)

                    def transact():
                        db_obj = db.Get(skel["key"])
                        db_obj[f"_viur_compute_{name}_"] = now
                        db_obj[name] = value
                        db.Put(db_obj)

                    if db.IsInTransaction():
                        transact()
                    else:
                        db.RunInTransaction(transact)

                    return True

            # Compute on every deserialization
            case ComputeMethod.Always:
                skel.accessedValues[name] = self._compute(skel, name)
                return True

        return False


class CartNodeSkel(TreeSkel):  # STATE: Complete (as in model)
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

    @property
    def total_without_shipping(self):
        return TotalFactory("total", lambda child: child.price_.current, True)(self, self.total)

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


class CartItemSkel(TreeSkel):  # STATE: Complete (as in model)
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
    def article_skel_full(self) -> SkeletonInstance:
        # TODO: Cache this property
        # logger.debug(f'Reading article_skel_full {self.article_skel["key"]=}')
        skel = SHOP_INSTANCE.get().article_skel()
        assert skel.read(self.article_skel["key"])
        return skel

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

    price = RawBone(  # FIXME: JsonBone doesn't work (https://github.com/viur-framework/viur-core/issues/1092)
        compute=Compute(lambda skel: skel.price_.to_dict(), ComputeInterval(ComputeMethod.Always))
    )
    price.type = JsonBone.type

    shipping = RawBone(  # FIXME: JsonBone doesn't work (https://github.com/viur-framework/viur-core/issues/1092)
        compute=Compute(
            lambda skel: make_json_dumpable(
                SHOP_INSTANCE.get().shipping.choose_shipping_skel_for_article(skel.article_skel_full)
            ),
            ComputeInterval(ComputeMethod.Always)),
    )
    shipping.type = JsonBone.type
