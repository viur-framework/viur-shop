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
    )

    salutation = SelectBone(
        values=Salutation,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
    )

    company_name = StringBone(
    )

    firstname = StringBone(
    )

    lastname = StringBone(
    )

    street_name = StringBone(
    )

    street_number = StringBone(
    )

    address_addition = StringBone(
    )

    zip_code = StringBone(
    )

    city = StringBone(
    )

    country = SelectCountryBone(
    )

    customer = RelationalBone(
        kind="user",
    )

    is_default = BooleanBone(
    )

    address_type = SelectBone(
        values=AddressType,
        translation_key_prefix=translation_key_prefix_skeleton_bonename,
    )

    cloned_from = RelationalBone(
        kind="shop_address",
        module="shop/address",
        readOnly=True,  # set by the system
        consistency=RelationalConsistency.Ignore,
    )
