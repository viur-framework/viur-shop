"""
ViUR-Shop – A modular e-commerce extension for the ViUR framework.

This package provides core components and modules for integrating
e-commerce functionality into ViUR-based projects. It includes
handling of shopping carts, orders, payment and shipping providers,
and is designed to be highly extensible and customizable.

Components included:

-   `shop`: The main module class that connects routing and core logic.
-   `cart`: Logic and utilities for managing shopping carts.
-   `order`: Models and logic for order processing.
-   `providers`: Registration system for pluggable payment and shipping providers.
-   `utils`: Shared utilities used throughout the shop package.

.. note::
    This package is intended for use with the ViUR framework.
    Only a single shop instance per project is currently supported.
"""

from .types_global import *
from .globals import *
from .modules import *
from .payment_providers import *
from .shop import Shop
from .skeletons import *
from .types import *
