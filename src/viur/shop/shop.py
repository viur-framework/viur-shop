import copy
import typing as t

from viur.core import conf, logging
from viur.core.bones import RelationalBone
from viur.core.module import Module
from viur.core.modules.translation import Creator, TranslationSkel
from viur.core.modules.user import UserSkel
from viur.core.prototypes.instanced_module import InstancedModule
from viur.core.render.abstract import AbstractRenderer
from viur.core.skeleton import MetaSkel, skeletonByKind
from viur.shop.data.translations import TRANSLATIONS
from viur.shop.skeletons.article import ArticleAbstractSkel
from .globals import SHOP_INSTANCE, SHOP_INSTANCE_VI, SHOP_LOGGER
from .modules import Address, Api, Cart, Discount, DiscountCondition, Order, Shipping, ShippingConfig, VatRate
from .payment_providers import PaymentProviderAbstract
from .services.hooks import HOOK_SERVICE
from .skeletons.discount import DiscountSkel
from .skeletons.discount_condition import DiscountConditionSkel
from .types import Supplier, exceptions

logger = SHOP_LOGGER.getChild(__name__)

__all__ = ["Shop"]

if SHOP_LOGGER.level == logging.NOTSET:
    # By default, if not explicitly set before by the application, we set the logging level to INFO
    SHOP_LOGGER.setLevel(logging.INFO)


class Shop(InstancedModule, Module):
    """
    A ViUR module providing core shop functionality such as cart handling,
    order processing, and integration with shipping and payment providers.

    This class serves as the central module for the `viur-shop` extension,
    offering routing and logic for managing shopping carts, creating and
    finalizing orders, and communicating with pluggable payment and shipping
    systems.

    Currently, only one instance of this module is supported per project.

    .. note::
        This module assumes integration with the ViUR framework and is not
        intended to be used standalone.
    """

    _is_registered_for: t.ClassVar[set[str]] = set()

    def __init__(
        self,
        *,
        name: str,
        article_skel: t.Type[ArticleAbstractSkel],
        payment_providers: list[PaymentProviderAbstract],
        suppliers: list[Supplier],
        admin_info_module_group: str | None = "viur-shop",
        # classes
        address_cls: t.Type[Address] = Address,
        api_cls: t.Type[Api] = Api,
        cart_cls: t.Type[Cart] = Cart,
        discount_cls: t.Type[Discount] = Discount,
        discount_condition_cls: t.Type[DiscountCondition] = DiscountCondition,
        order_cls: t.Type[Order] = Order,
        shipping_cls: t.Type[Shipping] = Shipping,
        shipping_config_cls: t.Type[ShippingConfig] = ShippingConfig,
        vat_rate_cls: t.Type[VatRate] = VatRate,
        #
        **kwargs: t.Any,
    ):
        # logger.debug(f"{self.__class__.__name__}<Shop>.__init__()")
        super().__init__()
        self.hooks = HOOK_SERVICE

        # Store arguments
        self.name: str = name
        self.article_skel: t.Type[ArticleAbstractSkel] = article_skel
        self.payment_providers: list[PaymentProviderAbstract] = payment_providers
        self.suppliers: list[Supplier] = suppliers
        self.admin_info_module_group: str | None = admin_info_module_group
        self.address_cls = address_cls
        self.api_cls = api_cls
        self.cart_cls = cart_cls
        self.discount_cls = discount_cls
        self.discount_condition_cls = discount_condition_cls
        self.order_cls = order_cls
        self.shipping_cls = shipping_cls
        self.shipping_config_cls = shipping_config_cls
        self.vat_rate_cls = vat_rate_cls
        self.additional_settings: dict[str, t.Any] = dict(kwargs)

        # Debug only
        # logger.debug(f"{vars(self) = }")
        self._add_translations()

    def __call__(self, *args, **kwargs) -> t.Self:
        # logger.debug(f"Shop.__call__({args=}, {kwargs=})")
        self: Shop = super().__call__(*args, **kwargs)  # noqa
        is_default_renderer = self.modulePath == f"/{self.moduleName}"

        # Modify some objects dynamically
        self._set_kind_names()
        self._extend_user_skeleton()
        self._extend_ref_keys()

        # Add sub modules
        self.address = self.address_cls(shop=self)
        self.api = self.api_cls(shop=self)
        self.cart = self.cart_cls(shop=self)
        self.discount = self.discount_cls(shop=self)
        self.discount_condition = self.discount_condition_cls(moduleName="discount_condition", shop=self)
        self.order = self.order_cls(shop=self)
        self.shipping = self.shipping_cls(shop=self)
        self.shipping_config = self.shipping_config_cls(moduleName="shipping_config", shop=self)
        self.vat_rate = self.vat_rate_cls(shop=self)

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

    def register(self, target: dict, render: AbstractRenderer) -> None:
        """
        Overwritten to avoid loops.
        The modules have an `shop` root/parent reference, but this should
        not again be discovered by :meth:`register`.
        """
        # logging.debug(f"{self.__class__.__name__}.register() {self.moduleName=} {self.modulePath=} "
        #               f"{id(target)=} {render=} {self._is_registered_for=}")
        if (render_name := f"{type(render).__module__}.{type(render).__qualname__}") in Shop._is_registered_for:
            return
        Shop._is_registered_for.add(render_name)
        return super().register(target, render)

    def _set_kind_names(self) -> None:
        """Set kindname of bones where the kind name can be dynamically

        At this point we are and must be before setSystemInitialized.
        """
        from viur.core.skeleton import getSystemInitialized, MetaBaseSkel
        if getSystemInitialized():
            raise exceptions.InvalidStateError(
                "The system cannot be initialized before the viur-shop is not prepared!"
            )
        from viur.shop import CartItemSkel  # import must stay here to avoid circular imports
        CartItemSkel.article.kind = self.article_skel.kindName
        CartItemSkel.article.module = self.article_skel.kindName
        DiscountConditionSkel.scope_article.kind = self.article_skel.kindName
        DiscountConditionSkel.scope_article.module = self.article_skel.kindName
        DiscountSkel.free_article.kind = self.article_skel.kindName
        DiscountSkel.free_article.module = self.article_skel.kindName

        # logger.debug(f"BEFORE {MetaBaseSkel._skelCache.keys() = }")
        # logger.debug(f"BEFORE {MetaBaseSkel._skelCache = }")

        # Replace {{viur_shop_modulename}} with real modulename in viur-shop Skeletons and bones
        for kindname, skel_cls in list(MetaBaseSkel._skelCache.items()):
            if not kindname.startswith("{{viur_shop_modulename}}_"):
                continue

            skel_cls.kindName = kindname.replace("{{viur_shop_modulename}}", self.moduleName)
            MetaBaseSkel._skelCache.pop(kindname)
            MetaBaseSkel._skelCache[skel_cls.kindName] = skel_cls

            for _bone_name, _bone_instance in skel_cls.__boneMap__.items():
                if isinstance(_bone_instance, RelationalBone):
                    # logger.debug(f"{_bone_name=} | {_bone_instance=}")
                    if _bone_instance.kind.startswith("{{viur_shop_modulename}}_"):
                        _bone_instance.kind = _bone_instance.kind.replace(
                            "{{viur_shop_modulename}}", self.moduleName)
                    if _bone_instance.module.startswith("{{viur_shop_modulename}}/"):
                        _bone_instance.module = _bone_instance.module.replace(
                            "{{viur_shop_modulename}}", self.moduleName)

        # logger.debug(f"AFTER {MetaBaseSkel._skelCache.keys() = }")
        # logger.debug(f"AFTER {MetaBaseSkel._skelCache = }")

    def _extend_user_skeleton(self) -> None:
        """Extend the UserSkel of the project

        At this point we are and must be before setSystemInitialized.
        """
        skel_cls: UserSkel = skeletonByKind("user")  # noqa
        # Add bone(s) needed by the shop
        skel_cls.wishlist = RelationalBone(
            descr="wishlist",
            kind=f"{self.moduleName}_cart_node",
            module=f"{self.moduleName}/cart",
            multiple=True,
        )
        skel_cls.basket = RelationalBone(
            descr="basket",
            kind=f"{self.moduleName}_cart_node",
            module=f"{self.moduleName}/cart",
        )
        # rebuild bonemap
        skel_cls.__boneMap__ = MetaSkel.generate_bonemap(skel_cls)

    def _extend_ref_keys(self) -> None:
        """Extend the refKeys of the implemented ArticleAbstractSkel

        At this point we are and must be before setSystemInitialized.
        """
        self.article_skel.shop_shipping_config.refKeys |= {"name", "shipping"}

    def _add_translations(self) -> None:
        """Setup translations required for the viur-shop"""
        if not conf.i18n.add_missing_translations:
            return

        for key, tr_dict in TRANSLATIONS.items():
            # Ensure lowercase key
            key = key.lower()
            skel = TranslationSkel().all().filter("name =", key).getSkel()
            if skel is None:
                skel = TranslationSkel().all().filter("tr_key =", key).getSkel()  # TODO: legacy viur-core
            if skel is not None:
                old_translations = copy.deepcopy(
                    (skel["translations"], skel["default_text"], skel["hint"], skel["public"])
                )
                for lang, value in tr_dict.items():
                    if lang in skel.translations.languages:
                        skel["translations"][lang] = skel["translations"].get(lang) or value
                skel["default_text"] = skel["default_text"] or tr_dict.get("_default_text") or ""
                skel["hint"] = skel["hint"] or tr_dict.get("_hint") or ""
                skel["public"] = True
                if old_translations != (skel["translations"], skel["default_text"], skel["hint"], skel["public"]):
                    logger.info(f"Update existing translation {key}")
                    logger.debug(f'{old_translations} --> {skel["translations"], skel["default_text"], skel["hint"]}')
                    try:
                        skel.write()
                    except Exception as exc:
                        logger.exception(f"Failed to write updated translation {skel=} :: {exc}")
                continue
            logger.info(f"Add missing translation {key}")
            skel = TranslationSkel()
            skel["tr_key"] = key  # TODO: legacy viur-core
            skel["name"] = key
            skel["translations"] = tr_dict
            skel["default_text"] = tr_dict.get("_default_text") or None
            skel["hint"] = tr_dict.get("_hint") or None
            skel["creator"] = Creator.VIUR
            skel["public"] = True
            try:
                skel.write()
            except Exception as exc:
                logger.exception(f"Failed to write added translation {skel=} :: {exc}")

    def __repr__(self) -> str:
        cls = type(self)
        return (
            f'<{cls.__module__}.{cls.__qualname__} object'
            f'with moduleName={getattr(self, "moduleName", "NOT_SET")}, '
            f'modulePath={getattr(self, "modulePath", "NOT_SET")}, '
            f'render={getattr(self, "render", "NOT_SET")}'
            f'at {hex(id(self))}>'
        )


Shop.html = True
Shop.vi = True
Shop.json = True
