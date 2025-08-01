# This is the place where the viur-shop version number is defined;
# For pre-releases, postfix with ".betaN" or ".rcN" where `N` is an incremented number for each pre-release.
# This will mark it as a pre-release as well on PyPI.

__version__ = "0.5.1"

assert __version__.count(".") >= 2 and "".join(__version__.split(".", 3)[:3]).isdigit(), \
    "Semantic __version__ expected!"
