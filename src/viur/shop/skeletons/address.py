from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.types import *
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


# TODO: should these bones required or will this be handled in a editSkel?

class AddressSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "{{viur_shop_modulename}}_address"

    name = StringBone(
        descr="Name",
        compute=Compute(
            lambda skel: f'{skel["salutation"]} {skel["firstname"]} {skel["lastname"]}'.strip(),
            ComputeInterval(ComputeMethod.OnWrite),
        ),
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
    )

    firstname = StringBone(
        params={"group": "Customer Info"},
        required=True,
    )

    lastname = StringBone(
        params={"group": "Customer Info"},
        required=True,
    )

    street_name = StringBone(
        params={"group": "Customer Address"},
        required=True,
    )

    street_number = StringBone(
        params={"group": "Customer Address"},
        required=True,
    )

    address_addition = StringBone(
        params={"group": "Customer Address"},
    )

    zip_code = StringBone(
        params={"group": "Customer Address"},
        required=True,
    )

    city = StringBone(
        params={"group": "Customer Address"},
        required=True,
    )

    country = SelectCountryBone(
        params={"group": "Customer Address"},
        required=True,
    )

    customer = RelationalBone(
        kind="user",
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
