from pathlib import Path

from viur.core import conf, translate
from viur.core.bones import BaseBone
from viur.core.skeleton import BaseSkeleton

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

# tmp used to generate translation dict
_tr = {}

# Set translated description of the bones using a schema with the bone name
for _key, _value in locals().copy().items():
    if isinstance(_value, type) and issubclass(_value, BaseSkeleton) and _value.__module__.startswith("viur.shop"):
        for _bone_name, _bone_instance in vars(_value).items():
            if isinstance(_bone_instance, BaseBone):
                _bone_instance.descr = translate(
                    f'viur.shop.skeleton.{_value.__name__.removesuffix("Skel").lower()}.{_bone_name}',
                    _bone_name,
                    f"bone {_bone_name}<{type(_bone_instance).__name__}> in {_value.__name__} in viur.shop"
                )
                _tr[_bone_instance.descr.key] = {
                    "en": _bone_name.replace("_", " ").capitalize(),
                    "fr": "",
                    "de": "",
                    "_hint": _bone_instance.descr.hint,
                }

# pprint(tr)
