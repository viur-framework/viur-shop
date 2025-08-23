"""
Specific exceptions used inside ViUR Shop
"""

from __future__ import annotations

import typing as t

from deprecated.sphinx import deprecated

from viur.core import errors
from ..types_global import Sentinel

if t.TYPE_CHECKING:
    from viur.shop.services import Hook

_SENTINEL: t.Final[Sentinel] = Sentinel()
"""Unique sentinel object used to detect if a argument was explicitly set or not"""


class ViURShopException(Exception):
    """Base of all ViUR Shop exceptions"""
    ...


class InvalidStateError(ViURShopException):
    """
    Exception raised when an object or resource (for the requested operation)
    is in a state that should not occur or is not permitted for this operation.
    """
    ...


class ConfigurationError(ViURShopException):
    """
    Exception raised when a configuration is invalid or incomplete.

    This may occur if required settings are missing, have incorrect values, or
    cause conflicts that prevent proper operation.
    Settings may also be required in the form of a skeleton, such as ``VatSkel``.
    """
    ...


class IllegalOperationError(ViURShopException):
    """
    Exception raised when an operation is not permitted in the current context.

    This usually signals that the requested action violates business rules,
    security constraints, or logical limitations of the system.
    """
    ...


class DispatchError(ViURShopException):
    """
    Exception raised when dispatch fails (e.g. a Hook).
    """

    def __init__(self, msg: t.Any, hook: Hook, *args: t.Any) -> None:
        """Create a new DispatchError.

        :param msg: Error message
        :param hook: The hook tried to dispatch
        """
        super().__init__(msg, *args)
        self.hook: Hook = hook


class ViURShopHttpException(errors.HTTPException):
    """Base of all ViUR Shop HTTP exceptions"""
    ...


# Use custom (unassigned) error codes, starting at 460
# see https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

class InvalidArgumentException(ViURShopHttpException):
    """
    Exception raised when a function receives an invalid value for an argument.

    **HTTP response status code:** ``460 Invalid Parameter``
    """

    def __init__(
        self,
        argument_name: str,
        argument_value: t.Any = _SENTINEL,
        descr_appendix: str = "",
    ):
        """Create a new TooManyArgumentsException.

        :param argument_name: Names of the invalid argument passed to the function.
        :param argument_value: Value of the invalid argument passed to the function.
        :param descr_appendix: Optional description for this error.
        """
        self.argument_name = argument_name
        self.argument_value = argument_value
        self.descr_appendix = descr_appendix
        msg = f"Invalid value"
        if argument_value is not _SENTINEL:
            msg += f" '{argument_value}'"
        msg += f" for parameter {argument_name}"
        if descr_appendix:
            msg += f". {descr_appendix}"
        super().__init__(
            status=460,
            name="Invalid Parameter",
            descr=msg,
        )


@deprecated(
    reason="Use InvalidArgumentException instead",
    version="0.6.0",
)
class InvalidKeyException(ViURShopHttpException):
    # TODO: Remove in a future version
    def __init__(self, key: str, argument_name: str = "key"):
        self.key = key
        self.argument_name = argument_name
        super().__init__(
            status=461, name="Invalid Parameter",
            descr=f"The provided key '{key}' (parameter {argument_name}) is not a valid db.Key",
        )


class TooManyArgumentsException(ViURShopHttpException):
    """
    Exception raised when a function receives unknown or excessive arguments.

    **HTTP response status code:** ``462 Too Many Arguments``
    """

    def __init__(self, func_name: str, *argument_names: str):
        """Create a new TooManyArgumentsException.

        :param func_nam: The name of the function where the error occurred.
        :param argument_names: Names of the unexpected arguments passed to the function.
        """
        self.func_name = func_name
        self.argument_names: tuple[str, ...] = argument_names
        super().__init__(
            status=462, name="Too Many Arguments",
            descr=f"{func_name} got too many (unknown) arguments: {', '.join(argument_names)}",
        )


class MissingArgumentsException(ViURShopHttpException):
    """
    Exception raised when one or more required arguments are missing in a function call.

    **HTTP response status code:** ``463 Missing Arguments``
    """

    def __init__(self, func_name: str, *argument_names: str, one_of: bool = False):
        """Create a new MissingArgumentsException.

        :param func_nam: The name of the function where the error occurred.
        :param argument_name: Names of the unexpected arguments passed to the function.
        :param one_of: If True, indicates that at least one of the listed arguments is required
               (logical OR). If False, all listed arguments are required (logical AND).
        """
        self.func_name = func_name
        self.argument_names: tuple[str, ...] = argument_names
        self.one_of: bool = one_of
        super().__init__(
            status=463, name="Missing Arguments",
            descr=(
                f"{func_name} is missing at least one of the required arguments: {' or '.join(argument_names)}"
                if one_of else
                f"{func_name} is missing the required arguments: {', '.join(argument_names)}"
            ),
        )
