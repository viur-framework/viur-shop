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
                "af": r"^\d{4}$",
                "ax": r"^\d{5}$",
                "al": r"^\d{4}$",
                "dz": r"^\d{5}$",
                "as": r"^\d{5}(-{1}\d{4,6})$",
                "ad": r"^[Aa][Dd]\d{3}$",
                "ao": r"",
                "ai": r"^[Aa][I][-][2][6][4][0]$",
                "ag": r"",
                "ar": r"^\d{4}|[A-Za-z]\d{4}[a-zA-Z]{3}$",
                "am": r"^\d{4}$",
                "aw": r"",
                "ac": r"^[Aa][Ss][Cc][Nn]\s{0,1}[1][Zz][Zz]$",
                "au": r"^\d{4}$",
                "at": r"^\d{4}$",
                "az": r"^[Aa][Zz]\d{4}$",
                "bs": r"",
                "bh": r"^\d{3,4}$",
                "bd": r"^\d{4}$",
                "bb": r"^[Aa][Zz]\d{5}$",
                "by": r"^\d{6}$",
                "be": r"^\d{4}$",
                "bz": r"",
                "bj": r"",
                "bm": r"^[A-Za-z]{2}\s([A-Za-z]{2}|\d{2})$",
                "bt": r"^\d{5}$",
                "bo": r"^\d{4}$",
                "bq": r"",
                "ba": r"^\d{5}$",
                "bw": r"",
                "br": r"^\d{5}-\d{3}$",
                "io": r"^[Bb]{2}[Nn][Dd]\s{0,1}[1][Zz]{2}$",
                "vg": r"^[Vv][Gg]\d{4}$",
                "bn": r"^[A-Za-z]{2}\d{4}$",
                "bg": r"^\d{4}$",
                "bf": r"",
                "bi": r"",
                "kh": r"^\d{5}$",
                "cm": r"",
                "ca": r"^(?=[^DdFfIiOoQqUu\d\s])[A-Za-z]\d(?=[^DdFfIiOoQqUu\d\s])[A-Za-z]\s{0,1}\d(?=[^DdFfIiOoQqUu\d\s])[A-Za-z]\d$",  # noqa
                "cv": r"^\d{4}$",
                "ky": r"^[Kk][Yy]\d[-\s]{0,1}\d{4}$",
                "cf": r"",
                "td": r"^\d{5}$",
                "cl": r"^\d{7}\s\(\d{3}-\d{4}\)$",
                "cn": r"^\d{6}$",
                "cx": r"^\d{4}$",
                "cc": r"^\d{4}$",
                "co": r"^\d{6}$",
                "km": r"",
                "cg": r"",
                "cd": r"^[Cc][Dd]$",
                "ck": r"",
                "cr": r"^\d{4,5}$",
                "ci": r"",
                "hr": r"^\d{5}$",
                "cu": r"^\d{5}$",
                "cw": r"",
                "cy": r"^\d{4}$",
                "cz": r"^\d{5}\s\(\d{3}\s\d{2}\)$",
                "dk": r"^\d{4}$",
                "dj": r"",
                "dm": r"",
                "do": r"^\d{5}$",
                "tl": r"",
                "ec": r"^\d{6}$",
                "sv": r"^1101$",
                "eg": r"^\d{5}$",
                "gq": r"",
                "er": r"",
                "ee": r"^\d{5}$",
                "et": r"^\d{4}$",
                "fk": r"^[Ff][Ii][Qq]{2}\s{0,1}[1][Zz]{2}$",
                "fo": r"^\d{3}$",
                "fj": r"",
                "fi": r"^\d{5}$",
                "fr": r"^\d{5}$",
                "gf": r"^973\d{2}$",
                "pf": r"^987\d{2}$",
                "tf": r"",
                "ga": r"^\d{2}\s[a-zA-Z-_ ]\s\d{2}$",
                "gm": r"",
                "ge": r"^\d{4}$",
                "de": r"^\d{5}$",
                "gh": r"",
                "gi": r"^[Gg][Xx][1]{2}\s{0,1}[1][Aa]{2}$",
                "gr": r"^\d{3}\s{0,1}\d{2}$",
                "gl": r"^\d{4}$",
                "gd": r"",
                "gp": r"^971\d{2}$",
                "gu": r"^\d{5}$",
                "gt": r"^\d{5}$",
                "gg": r"^[A-Za-z]{2}\d\s{0,1}\d[A-Za-z]{2}$",
                "gn": r"",
                "gw": r"^\d{4}$",
                "gy": r"",
                "ht": r"^\d{4}$",
                "hm": r"^\d{4}$",
                "hn": r"^\d{5}$",
                "hk": r"",
                "hu": r"^\d{4}$",
                "is": r"^\d{3}$",
                "in": r"^\d{6}$",
                "id": r"^\d{5}$",
                "ir": r"^\d{5}-\d{5}$",
                "iq": r"^\d{5}$",
                "ie": r"",
                "im": r"^[Ii][Mm]\d{1,2}\s\d[A-Z]{2}$",
                "il": r"^\b\d{5}(\d{2})?$",
                "it": r"^\d{5}$",
                "jm": r"^\d{2}$",
                "jp": r"^\d{7}\s\(\d{3}-\d{4}\)$",
                "je": r"^[Jj][Ee]\d\s{0,1}\d[A-Za-z]{2}$",
                "jo": r"^\d{5}$",
                "kz": r"^\d{6}$",
                "ke": r"^\d{5}$",
                "ki": r"",
                "kp": r"",
                "kr": r"^\d{6}\s\(\d{3}-\d{3}\)$",
                "xk": r"^\d{5}$",
                "kw": r"^\d{5}$",
                "kg": r"^\d{6}$",
                "lv": r"^[Ll][Vv][- ]{0,1}\d{4}$",
                "la": r"^\d{5}$",
                "lb": r"^\d{4}\s{0,1}\d{4}$",
                "ls": r"^\d{3}$",
                "lr": r"^\d{4}$",
                "ly": r"^\d{5}$",
                "li": r"^\d{4}$",
                "lt": r"^[Ll][Tt][- ]{0,1}\d{5}$",
                "lu": r"^\d{4}$",
                "mo": r"",
                "mk": r"^\d{4}$",
                "mg": r"^\d{3}$",
                "mw": r"",
                "mv": r"^\d{4,5}$",
                "my": r"^\d{5}$",
                "ml": r"",
                "mt": r"^[A-Za-z]{3}\s{0,1}\d{4}$",
                "mh": r"^\d{5}$",
                "mr": r"",
                "mu": r"",
                "mq": r"^972\d{2}$",
                "yt": r"^976\d{2}$",
                "fm": r"^\d{5}(-{1}\d{4})$",
                "mx": r"^\d{5}$",
                "md": r"^[Mm][Dd][- ]{0,1}\d{4}$",
                "mc": r"^980\d{2}$",
                "mn": r"^\d{5}$",
                "me": r"^\d{5}$",
                "ms": r"^[Mm][Ss][Rr]\s{0,1}\d{4}$",
                "ma": r"^\d{5}$",
                "mz": r"^\d{4}$",
                "mm": r"^\d{5}$",
                "na": r"^\d{5}$",
                "nr": r"",
                "np": r"^\d{5}$",
                "nl": r"^\d{4}\s{0,1}[A-Za-z]{2}$",
                "nc": r"^988\d{2}$",
                "nz": r"^\d{4}$",
                "ni": r"^\d{5}$",
                "ne": r"^\d{4}$",
                "ng": r"^\d{6}$",
                "nu": r"",
                "nf": r"^\d{4}$",
                "mp": r"^\d{5}$",
                "no": r"^\d{4}$",
                "om": r"^\d{3}$",
                "pk": r"^\d{5}$",
                "pw": r"^\d{5}$",
                "pa": r"^\d{6}$",
                "pg": r"^\d{3}$",
                "py": r"^\d{4}$",
                "pe": r"^\d{5}$",
                "ph": r"^\d{4}$",
                "pn": r"^[Pp][Cc][Rr][Nn]\s{0,1}[1][Zz]{2}$",
                "pl": r"^\d{2}[- ]{0,1}\d{3}$",
                "pt": r"^\d{4}[- ]{0,1}\d{3}$",
                "pr": r"^\d{5}$",
                "qa": r"",
                "re": r"^974\d{2}$",
                "ro": r"^\d{6}$",
                "ru": r"^\d{6}$",
                "bl": r"^97133$",
                "sh": r"^[Ss][Tt][Hh][Ll]\s{0,1}[1][Zz]{2}$",
                "kn": r"",
                "lc": r"",
                "mf": r"^97150$",
                "pm": r"^97500$",
                "vc": r"^[Vv][Cc]\d{4}$",
                "sm": r"^4789\d$",
                "st": r"",
                "sa": r"^\d{5}(-{1}\d{4})?$",
                "sn": r"",
                "rs": r"^\d{5}$",
                "sc": r"",
                "sx": r"",
                "sl": r"",
                "sg": r"^\d{6}$",
                "sk": r"^\d{5}\s\(\d{3}\s\d{2}\)$",
                "si": r"^([Ss][Ii][- ]{0,1}){0,1}\d{4}$",
                "sb": r"",
                "so": r"",
                "za": r"^\d{4}$",
                "gs": r"^[Ss][Ii][Qq]{2}\s{0,1}[1][Zz]{2}$",
                "es": r"^\d{5}$",
                "lk": r"^\d{5}$",
                "sd": r"^\d{5}$",
                "sr": r"",
                "sz": r"^[A-Za-z]\d{3}$",
                "se": r"^\d{3}\s*\d{2}$",
                "ch": r"^\d{4}$",
                "sj": r"^\d{4}$",
                "sy": r"",
                "tw": r"^\d{5}$",
                "tj": r"^\d{6}$",
                "tz": r"",
                "th": r"^\d{5}$",
                "tg": r"",
                "tk": r"",
                "to": r"",
                "tt": r"^\d{6}$",
                "tn": r"^\d{4}$",
                "tr": r"^\d{5}$",
                "tm": r"^\d{6}$",
                "tc": r"^[Tt][Kk][Cc][Aa]\s{0,1}[1][Zz]{2}$",
                "tv": r"",
                "ug": r"",
                "ua": r"^\d{5}$",
                "ae": r"",
                "gb": r"^[A-Z]{1,2}[0-9R][0-9A-Z]?\s*[0-9][A-Z-[CIKMOV]]{2}",
                "us": r"^\b\d{5}\b(?:[- ]{1}\d{4})?$",
                "uy": r"^\d{5}$",
                "vi": r"^\d{5}$",
                "uz": r"^\d{3} \d{3}$",
                "vu": r"",
                "va": r"^120$",
                "ve": r"^\d{4}(\s[a-zA-Z]{1})?$",
                "vn": r"^\d{6}$",
                "wf": r"^986\d{2}$",
                "ye": r"",
                "zm": r"^\d{5}$",
                "zw": r""
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
