import logging
import typing as t

from viur.core.bones import RelationalBone
from viur.core.decorators import exposed
from viur.core.module import Module
from viur.core.modules.user import UserSkel
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import MetaSkel, Skeleton, skeletonByKind
from .modules import *
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
        super().__init__()

        # Store arguments
        self.name: str = name
        self.article_skel: t.Type[Skeleton] = article_skel
        self.payment_providers: list[PaymentProviderAbstract] = payment_providers
        self.additional_settings: dict[str, t.Any] = dict(kwargs)

        # Debug only
        # logger.debug(f"{vars(self) = }")

    def __call__(self, *args, **kwargs):
        logger.debug(f"Shop.__call__({args=}, {kwargs=})")
        self: Shop = super().__call__(*args, **kwargs)  # noqa

        # Modify some objects dynamically
        self._set_kind_names()
        self._extend_user_skeleton()

        # Add sub modules
        self.address = Address(shop=self)
        self.api = Api(shop=self)
        self.cart = Cart(shop=self)
        self.discount = Discount(shop=self)
        self.discount_condition = DiscountCondition(moduleName="discount_condition", shop=self)
        self.order = Order(shop=self)
        self.shipping = Shipping(shop=self)
        self.shipping_config = ShippingConfig(moduleName="shipping_config", shop=self)
        self.vat = Vat(shop=self)
        self._update_methods()
        return self

    def _set_kind_names(self):
        """Set kindname of bones where the kind name can be dynamically

        At this point we are and must be before setSystemInitialized.
        """
        from viur.shop import CartItemSkel  # import must stay here to avoid circular imports
        CartItemSkel.article.kind = self.article_skel.kindName
        DiscountConditionSkel.scope_article.kind = self.article_skel.kindName
        DiscountConditionSkel.scope_article.module = self.article_skel.kindName

    def _extend_user_skeleton(self):
        """Extend the UserSkel of the project

        At this point we are and must be before setSystemInitialized.
        """
        skel_cls: UserSkel = skeletonByKind("user")  # noqa
        # Add bone(s) needed by the shop
        skel_cls.wishlist = RelationalBone(
            descr="wishlist",
            kind="shop_cart_node",
            module=f"{self.moduleName}/cart",
            multiple=True,
        )
        skel_cls.basket = RelationalBone(
            descr="basket",
            kind="shop_cart_node",
            module=f"{self.moduleName}/cart",
        )
        # rebuild bonemap
        skel_cls.__boneMap__ = MetaSkel.generate_bonemap(skel_cls)


Shop.html = True
Shop.vi = True
