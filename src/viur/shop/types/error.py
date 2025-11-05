"""
Classes and methods needed to handle errors
in order to produce reasonable API error responses.
"""

import functools
import string
import traceback
import types
import typing as t

from viur import toolkit  # noqa
from viur.core import current, errors as core_errors, i18n
from .response import JsonResponse
from ..globals import SHOP_LOGGER

try:
    from unzer import ErrorResponse as UnzerErrorResponse
except ImportError:  # extra not installed
    class UnzerErrorResponse(Exception):
        ...

logger = SHOP_LOGGER.getChild(__name__)

P = t.ParamSpec("P")
T = t.TypeVar("T")

HEADER_ALLOWED_CHARS = set(string.digits + string.ascii_letters + string.punctuation + " \t")


def clean_http_header(value: str, max_length: int = 1024) -> str:
    return "".join(c for c in value if c in HEADER_ALLOWED_CHARS)[:max_length]


class Error:
    """
    Represents a single error
    """
    __slots__ = ("code", "message", "customer_message", "exception", "details")

    def __init__(
        self,
        *,
        code: str,
        message: str | i18n.translate,
        customer_message: str | i18n.translate,
        exception: Exception,
        details: t.Any = None,
    ):
        self.code = code
        self.message = message
        self.customer_message = customer_message
        self.exception = exception
        self.details = details

    def as_json(self) -> dict[str, t.Any]:
        res = {
            "code": str(self.code),
            "message": str(self.message),
            "customer_message": str(self.customer_message),
            "details": self.details,
        }
        if self.exception:
            res["traceback"] = traceback.format_exception(self.exception)
        return res


class ErrorResponse:
    """
    API Error Response from errors.

    Represents an amount of one or multiple error(s), occurred during a request.
    """
    __slots__ = ("status_code", "errors")

    def __init__(
        self,
        *,
        errors: list[Error] | tuple[Error] = (),
        status_code: int = None,
    ):
        self.status_code = status_code or 500
        self.errors = list(errors)

    def as_json(self) -> dict[str, t.Any]:
        return {
            "errors": [
                error.as_json() for error in self.errors
            ],
        }

    def __str__(self) -> str:
        # logger.debug(f"Called __str__ on ErrorResponse")
        json_data = self.as_json()
        headers = current.request.get().response.headers
        headers["x-viur-shop-error"] = "1"  # indicator, it's from shop
        headers["x-viur-error"] = clean_http_header(", ".join(  # summary
            err.get("message", "") for err in json_data["errors"]
        ))
        return str(JsonResponse(
            json_data,
            status_code=self.status_code,
        ))

    @classmethod
    def from_exception(
        cls,
        *,
        exception: Exception,
    ) -> t.Self:
        if isinstance(exception, UnzerErrorResponse):
            return cls(
                errors=[
                    Error(
                        code=error.code,
                        message=error.merchantMessage,
                        customer_message=error.customerMessage,
                        exception=exception,
                    )
                    for error in exception.errors
                ],
                status_code=exception.statusCode,
            )
        else:
            return cls(
                errors=[
                    Error(
                        code=exception.args[0],
                        message=exception.args[0],
                        customer_message=exception.args[0],
                        exception=exception,
                    ),
                ],
                status_code=500,
            )


def error_handler(
    func: t.Optional[t.Callable[P, T]] = None,
) -> t.Callable[P, str] | t.Callable[[t.Callable[P, T]], t.Callable[P, str]]:
    """API Error Handler

    Decorator that handles errors and returns the method/function response otherwise.
    """

    def outer_wrapper(f: t.Callable[P, T]) -> t.Callable[P, t.Any]:
        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> t.Any:
            try:
                return f(*args, **kwargs)
            except core_errors.HTTPException as exc:
                raise exc
            except Exception as exc:  # noqa
                logger.exception(exc)
                return ErrorResponse.from_exception(
                    exception=exc,
                )

        return wrapper

    if isinstance(func, (types.MethodType, types.FunctionType)):
        return outer_wrapper(func)  # @error_handler
    else:
        return outer_wrapper  # @error_handler() or @error_handler(**any_kwargs)
