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
                "ac": r"^[Aa][Ss][Cc][Nn]\s{0,1}[1][Zz][Zz]$",
                "ad": r"^[Aa][Dd]\d{3}$",
                "ae": r"",
                "af": r"^\d{4}$",
                "ag": r"",
                "ai": r"^[Aa][I][-][2][6][4][0]$",
                "al": r"^\d{4}$",
                "am": r"^\d{4}$",
                "ao": r"",
                "ar": r"^\d{4}|[A-Za-z]\d{4}[a-zA-Z]{3}$",
                "as": r"^\d{5}(-{1}\d{4,6})$",
                "at": r"^\d{4}$",
                "au": r"^\d{4}$",
                "aw": r"",
                "ax": r"^\d{5}$",
                "az": r"^[Aa][Zz]\d{4}$",
                "ba": r"^\d{5}$",
                "bb": r"^[Aa][Zz]\d{5}$",
                "bd": r"^\d{4}$",
                "be": r"^\d{4}$",
                "bf": r"",
                "bg": r"^\d{4}$",
                "bh": r"^\d{3,4}$",
                "bi": r"",
                "bj": r"",
                "bl": r"^97133$",
                "bm": r"^[A-Za-z]{2}\s([A-Za-z]{2}|\d{2})$",
                "bn": r"^[A-Za-z]{2}\d{4}$",
                "bo": r"^\d{4}$",
                "bq": r"",
                "br": r"^\d{5}-\d{3}$",
                "bs": r"",
                "bt": r"^\d{5}$",
                "bw": r"",
                "by": r"^\d{6}$",
                "bz": r"",
                "ca": r"^([A-CEGHJ-NPR-TVWXYZaeghj-npr-tvwxyz]\d){2}\s?\d[A-CEGHJ-NPR-TVWXYZaeghj-npr-tvwxyz]\d$",
                "cc": r"^\d{4}$",
                "cd": r"^[Cc][Dd]$",
                "cf": r"",
                "cg": r"",
                "ch": r"^\d{4}$",
                "ci": r"",
                "ck": r"",
                "cl": r"^\d{7}\s\(\d{3}-\d{4}\)$",
                "cm": r"",
                "cn": r"^\d{6}$",
                "co": r"^\d{6}$",
                "cr": r"^\d{4,5}$",
                "cu": r"^\d{5}$",
                "cv": r"^\d{4}$",
                "cw": r"",
                "cx": r"^\d{4}$",
                "cy": r"^\d{4}$",
                "cz": r"^\d{5}\s\(\d{3}\s\d{2}\)$",
                "de": r"^\d{5}$",
                "dj": r"",
                "dk": r"^\d{4}$",
                "dm": r"",
                "do": r"^\d{5}$",
                "dz": r"^\d{5}$",
                "ec": r"^\d{6}$",
                "ee": r"^\d{5}$",
                "eg": r"^\d{5}$",
                "er": r"",
                "es": r"^\d{5}$",
                "et": r"^\d{4}$",
                "fi": r"^\d{5}$",
                "fj": r"",
                "fk": r"^[Ff][Ii][Qq]{2}\s{0,1}[1][Zz]{2}$",
                "fm": r"^\d{5}(-{1}\d{4})$",
                "fo": r"^\d{3}$",
                "fr": r"^\d{5}$",
                "ga": r"^\d{2}\s[a-zA-Z-_ ]\s\d{2}$",
                "gb": r"^[A-Z]{1,2}[0-9R][0-9A-Z]?\s*[0-9][A-JLNP-Z]{2}$",
                "gd": r"",
                "ge": r"^\d{4}$",
                "gf": r"^973\d{2}$",
                "gg": r"^[A-Za-z]{2}\d\s{0,1}\d[A-Za-z]{2}$",
                "gh": r"",
                "gi": r"^[Gg][Xx][1]{2}\s{0,1}[1][Aa]{2}$",
                "gl": r"^\d{4}$",
                "gm": r"",
                "gn": r"",
                "gp": r"^971\d{2}$",
                "gq": r"",
                "gr": r"^\d{3}\s{0,1}\d{2}$",
                "gs": r"^[Ss][Ii][Qq]{2}\s{0,1}[1][Zz]{2}$",
                "gt": r"^\d{5}$",
                "gu": r"^\d{5}$",
                "gw": r"^\d{4}$",
                "gy": r"",
                "hk": r"",
                "hm": r"^\d{4}$",
                "hn": r"^\d{5}$",
                "hr": r"^\d{5}$",
                "ht": r"^\d{4}$",
                "hu": r"^\d{4}$",
                "id": r"^\d{5}$",
                "ie": r"",
                "il": r"^\b\d{5}(\d{2})?$",
                "im": r"^[Ii][Mm]\d{1,2}\s\d[A-Z]{2}$",
                "in": r"^\d{6}$",
                "io": r"^[Bb]{2}[Nn][Dd]\s{0,1}[1][Zz]{2}$",
                "iq": r"^\d{5}$",
                "ir": r"^\d{5}-\d{5}$",
                "is": r"^\d{3}$",
                "it": r"^\d{5}$",
                "je": r"^[Jj][Ee]\d\s{0,1}\d[A-Za-z]{2}$",
                "jm": r"^\d{2}$",
                "jo": r"^\d{5}$",
                "jp": r"^\d{7}\s\(\d{3}-\d{4}\)$",
                "ke": r"^\d{5}$",
                "kg": r"^\d{6}$",
                "kh": r"^\d{5}$",
                "ki": r"",
                "km": r"",
                "kn": r"",
                "kp": r"",
                "kr": r"^\d{6}\s\(\d{3}-\d{3}\)$",
                "kw": r"^\d{5}$",
                "ky": r"^[Kk][Yy]\d[-\s]{0,1}\d{4}$",
                "kz": r"^\d{6}$",
                "la": r"^\d{5}$",
                "lb": r"^\d{4}\s{0,1}\d{4}$",
                "lc": r"",
                "li": r"^\d{4}$",
                "lk": r"^\d{5}$",
                "lr": r"^\d{4}$",
                "ls": r"^\d{3}$",
                "lt": r"^[Ll][Tt][- ]{0,1}\d{5}$",
                "lu": r"^\d{4}$",
                "lv": r"^[Ll][Vv][- ]{0,1}\d{4}$",
                "ly": r"^\d{5}$",
                "ma": r"^\d{5}$",
                "mc": r"^980\d{2}$",
                "md": r"^[Mm][Dd][- ]{0,1}\d{4}$",
                "me": r"^\d{5}$",
                "mf": r"^97150$",
                "mg": r"^\d{3}$",
                "mh": r"^\d{5}$",
                "mk": r"^\d{4}$",
                "ml": r"",
                "mm": r"^\d{5}$",
                "mn": r"^\d{5}$",
                "mo": r"",
                "mp": r"^\d{5}$",
                "mq": r"^972\d{2}$",
                "mr": r"",
                "ms": r"^[Mm][Ss][Rr]\s{0,1}\d{4}$",
                "mt": r"^[A-Za-z]{3}\s{0,1}\d{4}$",
                "mu": r"",
                "mv": r"^\d{4,5}$",
                "mw": r"",
                "mx": r"^\d{5}$",
                "my": r"^\d{5}$",
                "mz": r"^\d{4}$",
                "na": r"^\d{5}$",
                "nc": r"^988\d{2}$",
                "ne": r"^\d{4}$",
                "nf": r"^\d{4}$",
                "ng": r"^\d{6}$",
                "ni": r"^\d{5}$",
                "nl": r"^\d{4}\s{0,1}[A-Za-z]{2}$",
                "no": r"^\d{4}$",
                "np": r"^\d{5}$",
                "nr": r"",
                "nu": r"",
                "nz": r"^\d{4}$",
                "om": r"^\d{3}$",
                "pa": r"^\d{6}$",
                "pe": r"^\d{5}$",
                "pf": r"^987\d{2}$",
                "pg": r"^\d{3}$",
                "ph": r"^\d{4}$",
                "pk": r"^\d{5}$",
                "pl": r"^\d{2}[- ]{0,1}\d{3}$",
                "pm": r"^97500$",
                "pn": r"^[Pp][Cc][Rr][Nn]\s{0,1}[1][Zz]{2}$",
                "pr": r"^\d{5}$",
                "pt": r"^\d{4}[- ]{0,1}\d{3}$",
                "pw": r"^\d{5}$",
                "py": r"^\d{4}$",
                "qa": r"",
                "re": r"^974\d{2}$",
                "ro": r"^\d{6}$",
                "rs": r"^\d{5}$",
                "ru": r"^\d{6}$",
                "sa": r"^\d{5}(-{1}\d{4})?$",
                "sb": r"",
                "sc": r"",
                "sd": r"^\d{5}$",
                "se": r"^\d{3}\s*\d{2}$",
                "sg": r"^\d{6}$",
                "sh": r"^[Ss][Tt][Hh][Ll]\s{0,1}[1][Zz]{2}$",
                "si": r"^([Ss][Ii][- ]{0,1}){0,1}\d{4}$",
                "sj": r"^\d{4}$",
                "sk": r"^\d{5}\s\(\d{3}\s\d{2}\)$",
                "sl": r"",
                "sm": r"^4789\d$",
                "sn": r"",
                "so": r"",
                "sr": r"",
                "st": r"",
                "sv": r"^1101$",
                "sx": r"",
                "sy": r"",
                "sz": r"^[A-Za-z]\d{3}$",
                "tc": r"^[Tt][Kk][Cc][Aa]\s{0,1}[1][Zz]{2}$",
                "td": r"^\d{5}$",
                "tf": r"",
                "tg": r"",
                "th": r"^\d{5}$",
                "tj": r"^\d{6}$",
                "tk": r"",
                "tl": r"",
                "tm": r"^\d{6}$",
                "tn": r"^\d{4}$",
                "to": r"",
                "tr": r"^\d{5}$",
                "tt": r"^\d{6}$",
                "tv": r"",
                "tw": r"^\d{5}$",
                "tz": r"",
                "ua": r"^\d{5}$",
                "ug": r"",
                "us": r"^\b\d{5}\b(?:[- ]{1}\d{4})?$",
                "uy": r"^\d{5}$",
                "uz": r"^\d{3} \d{3}$",
                "va": r"^120$",
                "vc": r"^[Vv][Cc]\d{4}$",
                "ve": r"^\d{4}(\s[a-zA-Z]{1})?$",
                "vg": r"^[Vv][Gg]\d{4}$",
                "vi": r"^\d{5}$",
                "vn": r"^\d{6}$",
                "vu": r"",
                "wf": r"^986\d{2}$",
                "xk": r"^\d{5}$",
                "ye": r"",
                "yt": r"^976\d{2}$",
                "za": r"^\d{4}$",
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
