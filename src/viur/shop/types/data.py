import dataclasses
import typing as t

from viur.core.i18n import translate


@dataclasses.dataclass
class Supplier:
    """Supplier definition"""

    key: str
    """Internal identifier"""

    name: str | translate
    """Public name"""


@dataclasses.dataclass
class ClientError:
    """Class to store information about client error"""

    message: str

    causes_failure: bool = True

    @classmethod
    def has_failing_error(cls, errors: list[t.Self]) -> bool:
        """Check if a list of ``ClientError``s has as error that cause failing."""
        for error in errors:
            if error.causes_failure:
                return True
        return False
