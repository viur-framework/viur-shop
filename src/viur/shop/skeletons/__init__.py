from pathlib import Path

from viur.core import conf

# Before we can import any skeleton we must allow this dir in the viur-core
_dir = str(Path(__file__).parent)
if _dir not in conf.skeleton_search_path:
    conf.skeleton_search_path.append(_dir)
    conf.skeleton_search_path.append(
        _dir
        .replace(str(conf.instance.project_base_path), "")
        .replace(str(conf.instance.core_base_path), "")
    )

from .address import AddressSkel
from .article import ArticleAbstractSkel
from .cart import CartNodeSkel, CartItemSkel
from .discount import DiscountSkel
from .discount_condition import DiscountConditionSkel
from .order import OrderSkel
from .shipping import ShippingSkel
from .shipping_config import ShippingConfigSkel
from .shipping_precondition import ShippingPreconditionRelSkel
from .vat import VatSkel
