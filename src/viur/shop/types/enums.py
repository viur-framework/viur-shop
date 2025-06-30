"""
A lot of enums used for SelectBones in Skeletons
"""

import enum


class ArticleAvailability(enum.Enum):
    """Defines the stock availability status of an article."""
    IN_STOCK = "instock"
    OUT_OF_STOCK = "outofstock"
    LIMITED = "limited"
    DISCONTINUED = "discontinued"
    PREORDER = "preorder"


class CartType(enum.Enum):
    """Distinguishes between different cart types, such as wishlist and active basket."""
    WISHLIST = "wishlist"
    BASKET = "basket"


class CustomerType(enum.Enum):
    """Specifies whether a customer is a private individual or a business."""
    PRIVATE = "private"
    BUSINESS = "business"


class Salutation(enum.Enum):
    """Represents the salutation used when addressing a customer."""
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class AddressType(enum.Enum):
    """Specifies whether an address is used for billing or shipping."""
    BILLING = "billing"
    SHIPPING = "shipping"


class CodeType(enum.Enum):
    """Defines how discount or voucher codes are applied and managed."""
    NONE = "none"
    INDIVIDUAL = "individual"
    UNIVERSAL = "universal"


class ApplicationDomain(enum.Enum):
    """Specifies where a discount or rule applies — in basket, article, or globally."""
    BASKET = "basket"
    ARTICLE = "article"
    ALL = "all"
    """not care / both(all) / None"""


class CustomerGroup(enum.Enum):
    """Defines customer segmentation for applying conditions like first-time buyer."""

    ALL = "all"
    """alle Kunden"""

    FIRST_ORDER = "first_order"
    """Erstbestellung"""

    FOLLOW_UP_ORDER = "follow_up_order"
    """Folgebestellung "Stammkunden" (mind. eine Bestellung)"""


class DiscountType(enum.Enum):
    """Specifies the kind of discount applied, e.g., percentage or free shipping."""

    PERCENTAGE = "percentage"
    """percentage"""

    ABSOLUTE = "absolute"
    """absolute"""

    FREE_ARTICLE = "free_article"
    """free-article (and cart easter egg)"""

    FREE_SHIPPING = "free_shipping"
    """free-shipping"""


class ConditionOperator(enum.Enum):
    """Defines whether all or at least one discount condition must be satisfied."""

    ONE_OF = "one_of"
    """One condition must be satisfied"""

    ALL = "all"
    """All conditions must be satisfied"""


class OrderState(enum.Enum):
    """Represents the current processing state of an order."""

    ORDERED = "ordered"
    """Customer completed this order and clicked on buy"""

    CHECKOUT_IN_PROGRESS = "checkout_in_progress"
    """Customer started the checkout"""

    PAID = "paid"
    """Payment completed"""

    RTS = "rts"
    """Ready To Send (but must not be paid)"""


class QuantityMode(enum.Enum):
    """Specifies how item quantities in the cart should be modified."""

    REPLACE = "replace"
    """Use the provided quantity as new value"""

    INCREASE = "increase"
    """Adds the provided quantity to the current value"""

    DECREASE = "decrease"
    """Subtract the provided quantity from the current value"""


class ShippingStatus(enum.Enum):
    """Defines how a shipping method was selected (e.g., by user or cheapest option)."""

    USER = "user"
    """Shipping selected by a user"""

    CHEAPEST = "cheapest"
    """Cheapest shipping selected"""

    MOST_EXPENSIVE = "most_expensive"
    """Most expensive shipping selected"""


class VatRateCategory(enum.StrEnum):
    """Categorizes different VAT rate categories in the EU applied to goods and services."""

    STANDARD = "standard"
    """Applies to most goods and services, with a minimum rate of 15% mandated by the EU."""

    REDUCED = "reduced"
    """Applies to specific goods and services (e.g., food, books), typically at rates above 5%."""

    SUPER_REDUCED = "super_reduced"
    """Special cases with rates below 5%, applied to essential goods or services in some countries."""

    ZERO = "zero"
    """Applies to specific goods and services with no VAT charged, such as exports or essential items."""


class DiscountValidationContext(enum.IntEnum):
    """Describes the evaluation context for checking discount conditions.

    Context in which a :class:`DiscountConditionScope` can be checked.
    """

    NORMAL = enum.auto()
    """Normal context, in real time e.g. for an article"""

    AUTOMATICALLY_PREVALIDATE = enum.auto()
    """Pre-Validate automatically discount for caching"""

    AUTOMATICALLY_LIVE = enum.auto()
    """Validate automatically discount in real time"""
