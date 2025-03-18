import typing as t  # noqa

from viur.core import translate
from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.types import *
from ..globals import SHOP_INSTANCE, SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


def get_payment_providers() -> dict[str, str | translate]:
    return {
        pp.name: pp.title
        for pp in SHOP_INSTANCE.get().payment_providers
    }


class OrderSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "{{viur_shop_modulename}}_order"

    billing_address = RelationalBone(
        kind="{{viur_shop_modulename}}_address",
        module="{{viur_shop_modulename}}/address",
        consistency=RelationalConsistency.PreventDeletion,
        refKeys=[
            "key", "name", "customer_type", "salutation", "company_name",
            "firstname", "lastname", "street_name", "street_number",
            "address_addition", "zip_code", "city", "country",
            "email", "phone",
            "is_default", "address_type",
        ],
        searchable=True,
    )

    customer = RelationalBone(
        kind="user",
        searchable=True,
    )

    cart = TreeNodeBone(
        kind="{{viur_shop_modulename}}_cart_node",
        module="{{viur_shop_modulename}}/cart",
        consistency=RelationalConsistency.PreventDeletion,
        refKeys=[
            "name",
            "total",
            "total_discount_price",
            "vat",
            "total_quantity",
            "shipping_address",
            "shipping",
            "project_data",
        ],
        params={
            "context": {
                "skelType": "node",
            },
        },
        searchable=True,
    )

    total = NumericBone(
        precision=2,
        min=0,
        # TODO: UnitBone / CurrencyBone
    )
    """Kopie der total vom gesamten Warenkorb"""

    order_uid = StringBone(
        unique=UniqueValue(UniqueLockMethod.SameValue, False, "UID must be unique"),
        searchable=True,
        # TODO: UidBone
    )
    """Bestellnummer"""

    payment_provider = SelectBone(
        values=get_payment_providers,
    )

    is_ordered = BooleanBone(
    )

    is_paid = BooleanBone(
    )

    is_rts = BooleanBone(
    )

    is_checkout_in_progress = BooleanBone(
    )

    state = SelectBone(
        values=OrderState,
        multiple=True,
        compute=Compute(lambda skel: [
            value
            for key, value in OrderState._value2member_map_.items()
            if skel[f"is_{key}"]
        ]),
    )

    email = EmailBone(
        readOnly=True,
    )
    """
    .. deprecated:: 0.1.0.dev36
        Use :py:attr:`shop.skeleton.AddressSkel.email` instead.
    """

    phone = StringBone(
        readOnly=True,
    )
    """
    .. deprecated:: 0.1.0.dev36
        Use :py:attr:`shop.skeleton.AddressSkel.phone` instead.
    """

    project_data = JsonBone(
    )
    """Zusätzliche Daten vom Projekt für eine Bestellung.
    Ggf. überlegen ob einzelne Bones durch Skeleton Modifizierung besser sind."""

    payment = JsonBone(
        defaultValue=lambda skel, self: {},
    )
