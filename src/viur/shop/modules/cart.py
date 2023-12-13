import logging

from viur.core import exposed
from viur.core.prototypes import Tree
from viur.shop.modules.abstract import ShopModuleAbstract
from ..skeletons.cart import CartItemSkel, CartNodeSkel

logger = logging.getLogger("viur.shop").getChild(__name__)


class Cart(ShopModuleAbstract, Tree):
    nodeSkelCls = CartNodeSkel
    leafSkelCls = CartItemSkel

    @exposed
    def index(self):
        return "your cart is empty -.-"
