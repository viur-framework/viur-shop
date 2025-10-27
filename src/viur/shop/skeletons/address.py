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
                "AF": r"^\d{4}$",
                "AX": r"^\d{5}$",
                "AL": r"^\d{4}$",
                "DZ": r"^\d{5}$",
                "AS": r"^\d{5}(-{1}\d{4,6})$",
                "AD": r"^[Aa][Dd]\d{3}$",
                "AO": r"",
                "AI": r"^[Aa][I][-][2][6][4][0]$",
                "AG": r"",
                "AR": r"^\d{4}|[A-Za-z]\d{4}[a-zA-Z]{3}$",
                "AM": r"^\d{4}$",
                "AW": r"",
                "AC": r"^[Aa][Ss][Cc][Nn]\s{0,1}[1][Zz][Zz]$",
                "AU": r"^\d{4}$",
                "AT": r"^\d{4}$",
                "AZ": r"^[Aa][Zz]\d{4}$",
                "BS": r"",
                "BH": r"^\d{3,4}$",
                "BD": r"^\d{4}$",
                "BB": r"^[Aa][Zz]\d{5}$",
                "BY": r"^\d{6}$",
                "BE": r"^\d{4}$",
                "BZ": r"",
                "BJ": r"",
                "BM": r"^[A-Za-z]{2}\s([A-Za-z]{2}|\d{2})$",
                "BT": r"^\d{5}$",
                "BO": r"^\d{4}$",
                "BQ": r"",
                "BA": r"^\d{5}$",
                "BW": r"",
                "BR": r"^\d{5}-\d{3}$",
                "IO": r"^[Bb]{2}[Nn][Dd]\s{0,1}[1][Zz]{2}$",
                "VG": r"^[Vv][Gg]\d{4}$",
                "BN": r"^[A-Za-z]{2}\d{4}$",
                "BG": r"^\d{4}$",
                "BF": r"",
                "BI": r"",
                "KH": r"^\d{5}$",
                "CM": r"",
                "CA": r"^(?=[^DdFfIiOoQqUu\d\s])[A-Za-z]\d(?=[^DdFfIiOoQqUu\d\s])[A-Za-z]\s{0,1}\d(?=[^DdFfIiOoQqUu\d\s])[A-Za-z]\d$",
                "CV": r"^\d{4}$",
                "KY": r"^[Kk][Yy]\d[-\s]{0,1}\d{4}$",
                "CF": r"",
                "TD": r"^\d{5}$",
                "CL": r"^\d{7}\s\(\d{3}-\d{4}\)$",
                "CN": r"^\d{6}$",
                "CX": r"^\d{4}$",
                "CC": r"^\d{4}$",
                "CO": r"^\d{6}$",
                "KM": r"",
                "CG": r"",
                "CD": r"^[Cc][Dd]$",
                "CK": r"",
                "CR": r"^\d{4,5}$",
                "CI": r"",
                "HR": r"^\d{5}$",
                "CU": r"^\d{5}$",
                "CW": r"",
                "CY": r"^\d{4}$",
                "CZ": r"^\d{5}\s\(\d{3}\s\d{2}\)$",
                "DK": r"^\d{4}$",
                "DJ": r"",
                "DM": r"",
                "DO": r"^\d{5}$",
                "TL": r"",
                "EC": r"^\d{6}$",
                "SV": r"^1101$",
                "EG": r"^\d{5}$",
                "GQ": r"",
                "ER": r"",
                "EE": r"^\d{5}$",
                "ET": r"^\d{4}$",
                "FK": r"^[Ff][Ii][Qq]{2}\s{0,1}[1][Zz]{2}$",
                "FO": r"^\d{3}$",
                "FJ": r"",
                "FI": r"^\d{5}$",
                "FR": r"^\d{5}$",
                "GF": r"^973\d{2}$",
                "PF": r"^987\d{2}$",
                "TF": r"",
                "GA": r"^\d{2}\s[a-zA-Z-_ ]\s\d{2}$",
                "GM": r"",
                "GE": r"^\d{4}$",
                "DE": r"^\d{5}$",
                "GH": r"",
                "GI": r"^[Gg][Xx][1]{2}\s{0,1}[1][Aa]{2}$",
                "GR": r"^\d{3}\s{0,1}\d{2}$",
                "GL": r"^\d{4}$",
                "GD": r"",
                "GP": r"^971\d{2}$",
                "GU": r"^\d{5}$",
                "GT": r"^\d{5}$",
                "GG": r"^[A-Za-z]{2}\d\s{0,1}\d[A-Za-z]{2}$",
                "GN": r"",
                "GW": r"^\d{4}$",
                "GY": r"",
                "HT": r"^\d{4}$",
                "HM": r"^\d{4}$",
                "HN": r"^\d{5}$",
                "HK": r"",
                "HU": r"^\d{4}$",
                "IS": r"^\d{3}$",
                "IN": r"^\d{6}$",
                "ID": r"^\d{5}$",
                "IR": r"^\d{5}-\d{5}$",
                "IQ": r"^\d{5}$",
                "IE": r"",
                "IM": r"^[Ii][Mm]\d{1,2}\s\d[A-Z]{2}$",
                "IL": r"^\b\d{5}(\d{2})?$",
                "IT": r"^\d{5}$",
                "JM": r"^\d{2}$",
                "JP": r"^\d{7}\s\(\d{3}-\d{4}\)$",
                "JE": r"^[Jj][Ee]\d\s{0,1}\d[A-Za-z]{2}$",
                "JO": r"^\d{5}$",
                "KZ": r"^\d{6}$",
                "KE": r"^\d{5}$",
                "KI": r"",
                "KP": r"",
                "KR": r"^\d{6}\s\(\d{3}-\d{3}\)$",
                "XK": r"^\d{5}$",
                "KW": r"^\d{5}$",
                "KG": r"^\d{6}$",
                "LV": r"^[Ll][Vv][- ]{0,1}\d{4}$",
                "LA": r"^\d{5}$",
                "LB": r"^\d{4}\s{0,1}\d{4}$",
                "LS": r"^\d{3}$",
                "LR": r"^\d{4}$",
                "LY": r"^\d{5}$",
                "LI": r"^\d{4}$",
                "LT": r"^[Ll][Tt][- ]{0,1}\d{5}$",
                "LU": r"^\d{4}$",
                "MO": r"",
                "MK": r"^\d{4}$",
                "MG": r"^\d{3}$",
                "MW": r"",
                "MV": r"^\d{4,5}$",
                "MY": r"^\d{5}$",
                "ML": r"",
                "MT": r"^[A-Za-z]{3}\s{0,1}\d{4}$",
                "MH": r"^\d{5}$",
                "MR": r"",
                "MU": r"",
                "MQ": r"^972\d{2}$",
                "YT": r"^976\d{2}$",
                "FM": r"^\d{5}(-{1}\d{4})$",
                "MX": r"^\d{5}$",
                "MD": r"^[Mm][Dd][- ]{0,1}\d{4}$",
                "MC": r"^980\d{2}$",
                "MN": r"^\d{5}$",
                "ME": r"^\d{5}$",
                "MS": r"^[Mm][Ss][Rr]\s{0,1}\d{4}$",
                "MA": r"^\d{5}$",
                "MZ": r"^\d{4}$",
                "MM": r"^\d{5}$",
                "NA": r"^\d{5}$",
                "NR": r"",
                "NP": r"^\d{5}$",
                "NL": r"^\d{4}\s{0,1}[A-Za-z]{2}$",
                "NC": r"^988\d{2}$",
                "NZ": r"^\d{4}$",
                "NI": r"^\d{5}$",
                "NE": r"^\d{4}$",
                "NG": r"^\d{6}$",
                "NU": r"",
                "NF": r"^\d{4}$",
                "MP": r"^\d{5}$",
                "NO": r"^\d{4}$",
                "OM": r"^\d{3}$",
                "PK": r"^\d{5}$",
                "PW": r"^\d{5}$",
                "PA": r"^\d{6}$",
                "PG": r"^\d{3}$",
                "PY": r"^\d{4}$",
                "PE": r"^\d{5}$",
                "PH": r"^\d{4}$",
                "PN": r"^[Pp][Cc][Rr][Nn]\s{0,1}[1][Zz]{2}$",
                "PL": r"^\d{2}[- ]{0,1}\d{3}$",
                "PT": r"^\d{4}[- ]{0,1}\d{3}$",
                "PR": r"^\d{5}$",
                "QA": r"",
                "RE": r"^974\d{2}$",
                "RO": r"^\d{6}$",
                "RU": r"^\d{6}$",
                "BL": r"^97133$",
                "SH": r"^[Ss][Tt][Hh][Ll]\s{0,1}[1][Zz]{2}$",
                "KN": r"",
                "LC": r"",
                "MF": r"^97150$",
                "PM": r"^97500$",
                "VC": r"^[Vv][Cc]\d{4}$",
                "SM": r"^4789\d$",
                "ST": r"",
                "SA": r"^\d{5}(-{1}\d{4})?$",
                "SN": r"^\d{5}$",
                "RS": r"^\d{5}$",
                "SC": r"",
                "SX": r"",
                "SL": r"",
                "SG": r"^\d{6}$",
                "SK": r"^\d{5}\s\(\d{3}\s\d{2}\)$",
                "SI": r"^([Ss][Ii][- ]{0,1}){0,1}\d{4}$",
                "SB": r"",
                "SO": r"",
                "ZA": r"^\d{4}$",
                "GS": r"^[Ss][Ii][Qq]{2}\s{0,1}[1][Zz]{2}$",
                "ES": r"^\d{5}$",
                "LK": r"^\d{5}$",
                "SD": r"^\d{5}$",
                "SR": r"",
                "SZ": r"^[A-Za-z]\d{3}$",
                "SE": r"^\d{3}\s*\d{2}$",
                "CH": r"^\d{4}$",
                "SJ": r"^\d{4}$",
                "SY": r"",
                "TW": r"^\d{5}$",
                "TJ": r"^\d{6}$",
                "TZ": r"",
                "TH": r"^\d{5}$",
                "TG": r"",
                "TK": r"",
                "TO": r"",
                "TT": r"^\d{6}$",
                "TN": r"^\d{4}$",
                "TR": r"^\d{5}$",
                "TM": r"^\d{6}$",
                "TC": r"^[Tt][Kk][Cc][Aa]\s{0,1}[1][Zz]{2}$",
                "TV": r"",
                "UG": r"",
                "UA": r"^\d{5}$",
                "AE": r"",
                "GB": r"^[A-Z]{1,2}[0-9R][0-9A-Z]?\s*[0-9][A-Z-[CIKMOV]]{2}",
                "US": r"^\b\d{5}\b(?:[- ]{1}\d{4})?$",
                "UY": r"^\d{5}$",
                "VI": r"^\d{5}$",
                "UZ": r"^\d{3} \d{3}$",
                "VU": r"",
                "VA": r"^120$",
                "VE": r"^\d{4}(\s[a-zA-Z]{1})?$",
                "VN": r"^\d{6}$",
                "WF": r"^986\d{2}$",
                "YE": r"",
                "ZM": r"^\d{5}$",
                "ZW": r""
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

    birthdate = DateBone(
        params={
            "group": "Customer Info",
        },
        localize=False,
        naive=True,
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
