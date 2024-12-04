"""
A lot of enums used for SelectBones in Skeletons
"""

import enum
import typing as t


class ArticleAvailability(enum.Enum):
    IN_STOCK = "instock"
    OUT_OF_STOCK = "outofstock"
    LIMITED = "limited"
    DISCONTINUED = "discontinued"
    PREORDER = "preorder"


class CartType(enum.Enum):
    WISHLIST = "wishlist"
    BASKET = "basket"


class CustomerType(enum.Enum):
    PRIVATE = "private"
    BUSINESS = "business"


class Salutation(enum.Enum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class AddressType(enum.Enum):
    BILLING = "billing"
    SHIPPING = "shipping"


class CodeType(enum.Enum):
    NONE = "none"
    INDIVIDUAL = "individual"
    UNIVERSAL = "universal"


class ApplicationDomain(enum.Enum):
    BASKET = "basket"
    ARTICLE = "article"
    ALL = "all"
    """not care / both(all) / None"""


class CustomerGroup(enum.Enum):
    ALL = "all"
    """alle Kunden"""

    FIRST_ORDER = "first_order"
    """Erstbestellung"""

    FOLLOW_UP_ORDER = "follow_up_order"
    """Folgebestellung "Stammkunden" (mind. eine Bestellung)"""


class DiscountType(enum.Enum):
    PERCENTAGE = "percentage"
    """percentage"""

    ABSOLUTE = "absolute"
    """absolute"""

    FREE_ARTICLE = "free_article"
    """free-article (and cart easter egg)"""

    FREE_SHIPPING = "free_shipping"
    """free-shipping"""


class ConditionOperator(enum.Enum):
    ONE_OF = "one_of"
    """One condition must be satisfied"""

    ALL = "all"
    """All conditions must be satisfied"""


class OrderState(enum.Enum):
    ORDERED = "ordered"
    """Customer completed this order and clicked on buy"""

    CHECKOUT_IN_PROGRESS = "checkout_in_progress"
    """Customer started the checkout"""

    PAID = "paid"
    """Payment completed"""

    RTS = "rts"
    """Ready To Send (but must not be paid)"""


class QuantityMode(enum.Enum):
    REPLACE = "replace"
    """Use the provided quantity as new value"""

    INCREASE = "increase"
    """Adds the provided quantity to the current value"""

    DECREASE = "decrease"
    """Subtract the provided quantity from the current value"""


class ShippingStatus(enum.Enum):
    USER = "user"
    """Shipping selected by a user"""

    CHEAPEST = "cheapest"
    """Cheapest shipping selected"""


class VatRateCategory(enum.StrEnum):
    """
    Enumeration for VAT rate categories in the EU.
    """
    STANDARD = "standard"
    """Applies to most goods and services, with a minimum rate of 15% mandated by the EU."""

    REDUCED = "reduced"
    """Applies to specific goods and services (e.g., food, books), typically at rates above 5%."""

    SUPER_REDUCED = "super_reduced"
    """Special cases with rates below 5%, applied to essential goods or services in some countries."""

    ZERO = "zero"
    """Applies to specific goods and services with no VAT charged, such as exports or essential items."""


QuantityModeType = t.Literal["replace", "increase", "decrease"]
