from pathlib import Path

from viur.core import conf

# Before we can import any skeleton we must allow this dir in the viur-core
_dir = str(Path(__file__).parent)
if _dir not in conf.skeleton_search_path:
    conf.skeleton_search_path.append(_dir)


from .article import ArticleAbstractSkel
from .cart import CartNodeSkel, CartItemSkel
from .shipping import ShippingSkel
from .vat import VatSkel

