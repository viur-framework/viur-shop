from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.types import *

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


# TODO: should these bones required or will this be handled in a editSkel?

class AddressSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_address"

    name = StringBone(
        descr="Name",
        compute=Compute(
            lambda skel: f'{skel["salutation"]} {skel["firstname"]} {skel["lastname"]}'.strip(),
            ComputeInterval(ComputeMethod.OnWrite),
        )
    )

    customer_type = SelectBone(
        values=CustomerType,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={"group": "Customer Info"}
    )

    salutation = SelectBone(
        values=Salutation,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={"group": "Customer Info"}
    )

    company_name = StringBone(
        params={"group": "Customer Info"}
    )

    firstname = StringBone(
        params={"group": "Customer Info"}
    )

    lastname = StringBone(
        params={"group": "Customer Info"}
    )

    street_name = StringBone(
        params={"group": "Customer Address"}
    )

    street_number = StringBone(
        params={"group": "Customer Address"}
    )

    address_addition = StringBone(
        params={"group": "Customer Address"}
    )

    zip_code = StringBone(
        params={"group": "Customer Address"}
    )

    city = StringBone(
        params={"group": "Customer Address"}
    )

    country = SelectCountryBone(
        params={"group": "Customer Address"}
    )

    customer = RelationalBone(
        kind="user",
    )

    is_default = BooleanBone(
    )

    address_type = SelectBone(
        values=AddressType,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
        params={"group": "Customer Address"}
    )

    cloned_from = RelationalBone(
        kind="shop_address",
        module="shop/address",
        readOnly=True,  # set by the system
        consistency=RelationalConsistency.Ignore,
    )
