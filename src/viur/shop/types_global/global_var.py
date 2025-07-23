import typing as t

from .sentinel import Sentinel

_T = t.TypeVar("_T")
"""The generic type of the value stored in the GlobalVar"""

_SENTINEL: t.Final[Sentinel] = Sentinel()
"""Unique sentinel object used to detect if a value was explicitly set or not"""


class GlobalVar(t.Generic[_T]):
    """
    A generic container for storing a global-like variable with optional default fallback.

    This class allows safe setting and retrieval of values, with
    optional fallbacks and error handling if no value is set.
    """

    __slots__ = ("name", "value")

    def __init__(self, name: str, default: _T = _SENTINEL):
        """
        Initialize a GlobalVar instance.

        :param name: The name of the global variable.
        :param default: Optional default value.
            If not provided, accessing the value via :meth:`get` will raise a LookupError if unset.
        """
        self.name = name
        self.value = default

    def set(self, value: _T) -> None:
        """
        Set the value of the variable.

        :param value: The value to assign to the global variable.
        """
        self.value = value

    def get(self, default: _T = _SENTINEL) -> _T:
        """
        Retrieve the stored value.

        If no value was explicitly set, returns the provided fallback,
        or raises a LookupError if neither a value nor fallback exists.

        :param default: Optional fallback value to return if no value is set.
        :return: The stored value or the provided default.
        :raises LookupError: If no value is set and no default is provided.
        """
        if self.value is not _SENTINEL:
            return self.value
        elif default is not _SENTINEL:
            return default
        else:
            raise LookupError(f"<{type(self).__name__} name={self.name!r} at {hex(id(self))}>")

    def __repr__(self) -> str:
        """
        Return a string representation of the GlobalVar instance.

        :return: A string representation showing the name and value.
        """
        return f"<{type(self).__name__} name={self.name!r} value={self.value!r}>"
