import logging
import typing as t

from viur.core.decorators import exposed
from viur.core.module import Module
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import Skeleton
from .modules import Cart
from .modules.api import Api
from .payment_providers import PaymentProviderAbstract
from .skeletons.discount_condition import DiscountConditionSkel

logger = logging.getLogger("viur.shop").getChild(__name__)


class Shop(InstancedModule, Module):
    @exposed
    def hello(self):
        return f"Welcome to the {self.name} Shop!"

    def __init__(
        self,
        name: str,
        article_skel: t.Type[Skeleton],
        payment_providers: list[PaymentProviderAbstract],
        *args, **kwargs,
    ):
        logger.debug(f"Shop.__init__()")
        super().__init__()

        # Store arguments
        self.name: str = name
        self.article_skel: t.Type[Skeleton] = article_skel
        self.payment_providers: list[PaymentProviderAbstract] = payment_providers
        self.additional_settings: dict[str, t.Any] = dict(kwargs)

        self._set_kind_names()

        # Debug only
        logger.debug(f"{vars(self) = }")

    def __call__(self, *args, **kwargs):
        logger.debug(f"Shop.__call__({args=}, {kwargs=})")
        self: Shop = super().__call__(*args, **kwargs)  # noqa
        # Add sub modules
        self.api = Api("api", f"{self.modulePath}/cart", shop=self)
        self.cart = Cart("cart", f"{self.modulePath}/cart", shop=self)
        self._update_methods()
        return self

    def _set_kind_names(self):
        """Set kindname of bones where the kind name can be dynamically

        At this point we are and must be before setSystemInitialized.
        """
        from viur.shop import CartItemSkel
        CartItemSkel.article.kind = self.article_skel.kindName
        DiscountConditionSkel.scope_article.kind = self.article_skel.kindName




Shop.html = True
Shop.vi = True
