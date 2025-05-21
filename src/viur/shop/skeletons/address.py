from viur.core import conf, current, i18n
from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.types import *
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class AddressSkel(Skeleton):
    kindName = "{{viur_shop_modulename}}_address"

    name = StringBone(
        descr="Name",
        compute=Compute(
            lambda skel: f'{skel["salutation"]} {skel["firstname"]} {skel["lastname"]}'.strip(),
            ComputeInterval(ComputeMethod.OnWrite),
        ),
        searchable=True,
    )

    customer_type = SelectBone(
        values=CustomerType,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={"group": "Customer Info"},
        required=True,
    )

    salutation = SelectBone(
        values=Salutation,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={"group": "Customer Info"},
        required=True,
    )

    company_name = StringBone(
        params={"group": "Customer Info"},
        searchable=True,
    )

    firstname = StringBone(
        params={"group": "Customer Info"},
        required=True,
        searchable=True,
    )

    lastname = StringBone(
        params={"group": "Customer Info"},
        required=True,
        searchable=True,
    )

    street_name = StringBone(
        params={"group": "Customer Address"},
        required=True,
        searchable=True,
    )

    street_number = StringBone(
        params={"group": "Customer Address"},
        required=True,
        searchable=True,
    )

    address_addition = StringBone(
        params={"group": "Customer Address"},
        searchable=True,
    )

    zip_code = StringBone(
        required=True,
        params={
            "group": "Customer Address",
            "pattern": {
                country: r"\d{4,5}"
                for country in conf.i18n.available_dialects
            },
            "pattern-error": i18n.translate(
                "viur.shop.skeleton.address.zip_code.invalid",
                public=True,
            ),
        },
        searchable=True,
    )

    city = StringBone(
        params={"group": "Customer Address"},
        required=True,
        searchable=True,
    )

    country = SelectCountryBone(
        params={"group": "Customer Address"},
        required=True,
        searchable=True,
    )

    customer = RelationalBone(
        kind="user",
    )

    email = EmailBone(
        required=True,
        defaultValue=lambda skel, bone: current.user.get() and current.user.get()["name"],
        params={
            "group": "Customer Info",
            "pattern": {
                # Pattern source: https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
                country: r"/^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/"  # noqa
                for country in conf.i18n.available_dialects
            },
            "pattern-error": i18n.translate(
                "viur.shop.skeleton.address.email.invalid",
                public=True,
            ),
        },
        searchable=True,
    )
    """Kopieren von User oder Eingabe von Nutzer bei Gast"""

    phone = StringBone(
        required=True,
        params={
            "group": "Customer Info",
            "pattern": {
                country: r"^\+?(?:[\-\|\/\s\(\)]*\d){5,}$"
                for country in conf.i18n.available_dialects
            },
            "pattern-error": i18n.translate(
                "viur.shop.skeleton.address.phone.invalid",
                public=True,
            ),
        },
        searchable=True,
    )

    # FIXME: What happens if an AddressSkel has both address_types and is_default
    #        and you add an new default AddressSkel with only one address_type?
    is_default = BooleanBone(
    )

    address_type = SelectBone(
        values=AddressType,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={"group": "Customer Address"},
        required=True,
        multiple=True,
    )

    cloned_from = RelationalBone(
        kind="{{viur_shop_modulename}}_address",
        module="{{viur_shop_modulename}}/address",
        readOnly=True,  # set by the system
        consistency=RelationalConsistency.Ignore,
    )
