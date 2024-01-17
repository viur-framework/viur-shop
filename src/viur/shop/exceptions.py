import typing as t

from viur.core import errors

_sentinel = object()


class ViURShopException(Exception):
    ...


class InvalidStateError(ViURShopException):
    ...


class ViURShopHttpException(errors.HTTPException):
    ...


# Use custom (unassigned) error codes, starting at 460
# see https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

class InvalidArgumentException(ViURShopHttpException):
    def __init__(
        self,
        argument_name: str,
        argument_value: t.Any = _sentinel,
        descr_appendix: str = "",
    ):
        self.argument_name = argument_name
        self.argument_value = argument_value
        self.descr_appendix = descr_appendix
        msg = f"Invalid value"
        if argument_value is not _sentinel:
            msg += f" '{argument_value}'"
        msg += f" for parameter {argument_name}"
        if descr_appendix:
            msg += f". {descr_appendix}"
        super().__init__(
            status=460,
            name="Invalid Parameter",
            descr=msg,
        )


class InvalidKeyException(ViURShopHttpException):
    # TODO: is this class really necessary or is InvalidArgumentException enough?
    def __init__(self, key: str, argument_name: str = "key"):
        self.key = key
        self.argument_name = argument_name
        super().__init__(
            status=461, name="Invalid Parameter",
            descr=f"The provided key '{key}' (parameter {argument_name}) is not a valid db.Key"
        )
