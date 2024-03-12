import dataclasses

from viur.core.i18n import translate


@dataclasses.dataclass
class Supplier:
    key: str
    """Internal identifier"""

    name: str | translate
    """Public name"""


@dataclasses.dataclass
class ClientError:
    message: str

    causes_failure: bool = True
