import enum


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
    NONE = None  # TODO: is this working?
    INDIVIDUAL = "individual"
    UNIVERSAL = "universal"


class ApplicationDomain(enum.Enum):
    BASKET = "basket"
    ARTICLE = "article"


class CustomerGroup(enum.Enum):
    NONE = None  # TODO: is this working?
    """none (alle Kunden)"""

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
    # TODO: Shall we name them "one" and "all" instead of "or" and "AND"?

    OR = "or"
    """One condition must be satisfied"""

    AND = "and"
    """All conditions must be satisfied"""


class OrderState(enum.Enum):
    ORDERED = "ordered"
    """Customer completed this order and clicked on buy"""

    PAID = "paid"
    """Payment completed"""

    RTS = "rts"
    """Ready To Send (but must not be paid)"""
