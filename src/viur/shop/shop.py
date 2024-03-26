import copy
import typing as t

from viur.core import conf
from viur.core.bones import RelationalBone
from viur.core.decorators import exposed
from viur.core.module import Module
from viur.core.modules.translation import Creator, TranslationSkel
from viur.core.modules.user import UserSkel
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.skeleton import MetaSkel, Skeleton, skeletonByKind
from viur.shop.data.translations import TRANSLATIONS
from .globals import SHOP_INSTANCE, SHOP_INSTANCE_VI, SHOP_LOGGER
from .modules import Address, Api, Cart, Discount, DiscountCondition, Order, Shipping, ShippingConfig, Vat
from .payment_providers import PaymentProviderAbstract
from .services.hooks import HOOK_SERVICE
from .skeletons.discount import DiscountSkel
from .skeletons.discount_condition import DiscountConditionSkel
from .types import Supplier

logger = SHOP_LOGGER.getChild(__name__)

__all__ = ["Shop"]


class Shop(InstancedModule, Module):
    @exposed
    def hello(self):
        # logger.debug(f"{SHOP_INSTANCE.get().render=}")
        # logger.debug(f"{SHOP_INSTANCE_VI.get().render=}")
        return f"Welcome to the {self.name} Shop!"

    def __init__(
        self,
        *,
        name: str,
        article_skel: t.Type[Skeleton],
        payment_providers: list[PaymentProviderAbstract],
        suppliers: list[Supplier],
        admin_info_module_group: str | None = "viur-shop",
        **kwargs,
    ):
        super().__init__()
        self.hooks = HOOK_SERVICE

        # Store arguments
        self.name: str = name
        self.article_skel: t.Type[Skeleton] = article_skel
        self.payment_providers: list[PaymentProviderAbstract] = payment_providers
        self.suppliers: list[Supplier] = suppliers
        self.admin_info_module_group: str | None = admin_info_module_group
        self.additional_settings: dict[str, t.Any] = dict(kwargs)

        # Debug only
        # logger.debug(f"{vars(self) = }")
        self._add_translations()

    def __call__(self, *args, **kwargs):
        logger.debug(f"Shop.__call__({args=}, {kwargs=})")
        self: Shop = super().__call__(*args, **kwargs)  # noqa
        is_default_renderer = self.modulePath == f"/{self.moduleName}"

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

        # Make payment_providers routable as sub modules
        for idx, pp in enumerate(self.payment_providers):
            module_name = f"pp_{pp.name}".replace("-", "_")
            original_pp = pp
            pp = pp(module_name, f"{self.modulePath}/{module_name}")
            pp.shop = self
            setattr(self, module_name, pp)
            # logger.debug(f"Saved {pp} ({vars(pp)}) under {module_name}")
            if is_default_renderer:
                original_pp.shop = self
                original_pp.moduleName = pp.moduleName
                original_pp.modulePath = pp.modulePath

        self._update_methods()

        # set the instance references
        if is_default_renderer:
            SHOP_INSTANCE.set(self)
        elif self.modulePath == f"/vi/{self.moduleName}":
            SHOP_INSTANCE_VI.set(self)
        return self

    def _set_kind_names(self):
        """Set kindname of bones where the kind name can be dynamically

        At this point we are and must be before setSystemInitialized.
        """
        from viur.shop import CartItemSkel  # import must stay here to avoid circular imports
        CartItemSkel.article.kind = self.article_skel.kindName
        DiscountConditionSkel.scope_article.kind = self.article_skel.kindName
        DiscountConditionSkel.scope_article.module = self.article_skel.kindName
        DiscountSkel.free_article.kind = self.article_skel.kindName
        DiscountSkel.free_article.module = self.article_skel.kindName

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

    def _add_translations(self):
        """Setup translations required for the viur-shop"""
        if not conf.i18n.add_missing_translations:
            return

        for key, tr_dict in TRANSLATIONS.items():
            # Ensure lowercase key
            key = key.lower()
            skel = TranslationSkel().all().filter("tr_key =", key).getSkel()
            if skel is not None:
                old_translations = copy.deepcopy((skel["translations"], skel["default_text"], skel["hint"]))
                for lang, value in tr_dict.items():
                    if lang in skel.translations.languages:
                        skel["translations"][lang] = skel["translations"].get(lang) or value
                skel["default_text"] = skel["default_text"] or tr_dict.get("_default_text") or None
                skel["hint"] = skel["hint"] or tr_dict.get("_hint") or None
                if old_translations != (skel["translations"], skel["default_text"], skel["hint"]):
                    logger.info(f"Update existing translation {key}")
                    logger.debug(f'{old_translations} --> {skel["translations"], skel["default_text"], skel["hint"]}')
                    skel.toDB()
                continue
            logger.info(f"Add missing translation {key}")
            skel = TranslationSkel()
            skel["tr_key"] = key
            skel["translations"] = tr_dict
            skel["default_text"] = tr_dict.get("_default_text") or None
            skel["hint"] = tr_dict.get("_hint") or None
            skel["creator"] = Creator.VIUR
            skel.toDB()


Shop.html = True
Shop.vi = True
Shop.json = True
