import logging

from viur.core.bones import *
from viur.core.skeleton import Skeleton
from viur.shop.constants import *

logger = logging.getLogger("viur.shop").getChild(__name__)


# TODO: should these bones required or will this be handled in a editSkel?

class AddressSkel(Skeleton):  # STATE: Complete (as in model)
    kindName = "shop_address"

    customer_type = SelectBone(
        descr="customer_type",
        values=CustomerType,
    )

    salutation = SelectBone(
        descr="salutation",
        values=Salutation,
    )

    company_name = StringBone(
        descr="company_name",
    )

    firstname = StringBone(
        descr="firstname",
    )

    lastname = StringBone(
        descr="lastname",
    )

    street_name = StringBone(
        descr="street_name",
    )

    street_number = StringBone(
        descr="street_number",
    )

    address_addition = StringBone(
        descr="address_addition",
    )

    zip_code = StringBone(
        descr="zip_code",
    )

    city = StringBone(
        descr="city",
    )

    country = SelectCountryBone(
        descr="country",
    )

    customer = RelationalBone(
        descr="customer",
        kind="user",
    )

    is_default = BooleanBone(
        descr="is_default",
    )

    address_type = SelectBone(
        descr="address_type",
        values=AddressType,
    )

    cloned_from = RelationalBone(
        descr="cloned_from",
        kind="shop_address",
        module="shop.address",
        readOnly=True,  # set by the system
        consistency=RelationalConsistency.Ignore,
    )
