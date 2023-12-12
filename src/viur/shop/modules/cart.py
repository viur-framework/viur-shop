import logging

from viur.core import exposed
from viur.shop.modules.abstract import ShopModuleAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


class Cart(ShopModuleAbstract):
    @exposed
    def index(self):
        return "your cart is empty -.-"
