"""
This module contains several kinds of validators to do the discount validation.

The structure of validators is:

.. code-block:: none

    DiscountValidator
    ├─ ConditionValidator
    │  ├─ DiscountConditionScope
    │  ├─ DiscountConditionScope
    │  └─ ...
    ├─ ConditionValidator
    │  ├─ DiscountConditionScope
    │  ├─ DiscountConditionScope
    │  └─ ...
    └─ ...


Each validator refers to a layer of the model

-   :class:`DiscountValidator` <-> :class:`DiscountSkel`
-   :class:`ConditionValidator` <-> :class:`DiscountConditionSkel`
-   :class:`DiscountConditionScope` <-> bones in :class:`DiscountConditionSkel`
"""

import abc
import pprint
import typing as t  # noqa
from datetime import timedelta as td

from viur.core import current, utils
from viur.core.skeleton import RefSkel, SkeletonInstance, skeletonByKind
from .enums import *
from .exceptions import DispatchError, InvalidStateError
from ..globals import SENTINEL, SHOP_INSTANCE, SHOP_LOGGER, Sentinel
from ..services import HOOK_SERVICE, Hook
from ..types import SkeletonInstance_T

if t.TYPE_CHECKING:
    from ..skeletons import ArticleAbstractSkel

logger = SHOP_LOGGER.getChild(__name__)


def _skel_repr(skel: SkeletonInstance_T | None) -> str:
    if skel is None:
        return "None"
    return f'<SkeletonInstance of {skel.skeletonCls.__name__} with key={skel["key"]} and name={skel["name"]}>'


class DiscountConditionScope(abc.ABC):
    """
    Validator that validates a specific discount condition scope.

    The scope is usually defined by one bone in the :class:`DiscountConditionSkel`.

    A scope is fulfilled if the precondition and the main condition are fulfilled.
    It is not fulfilled if the precondition is fulfilled but the main condition is not.
    If the precondition is not fulfilled, the scope is ignored (regardless of the main condition).
    """

    _is_applicable = None
    _is_fulfilled = None

    def __init__(
        self,
        *,
        cart_skel: SkeletonInstance_T["CartNodeSkel"] | None | Sentinel = SENTINEL,
        article_skel: SkeletonInstance_T["ArticleAbstractSkel"] | None | Sentinel = SENTINEL,
        discount_skel: SkeletonInstance_T["DiscountSkel"] | None | Sentinel = SENTINEL,
        code: str | None | Sentinel = SENTINEL,
        condition_skel: SkeletonInstance_T["DiscountConditionSkel"],
        context: DiscountValidationContext,
    ):
        self.cart_skel = cart_skel
        self.article_skel = article_skel
        self.discount_skel = discount_skel
        self.condition_skel = condition_skel
        self.code = code
        self.context = context

    def precondition(self) -> bool:
        """
        Validates the precondition for this scope.

        Usually this means the related bone in the :class:`DiscountConditionSkel` has a value defined.
        Unfulfilled preconditions make :class:``DiscountConditionScope`` no longer necessary.
        """
        return True

    allowed_contexts: t.Final[list[DiscountValidationContext]] = [
        DiscountValidationContext.NORMAL,
        DiscountValidationContext.AUTOMATICALLY_LIVE,
    ]
    """contexts in which this scope should be checked"""

    @abc.abstractmethod
    def __call__(self) -> bool:
        """
        The (main) condition of this scope.

        This check could be, for example, that:

            -   A bone of an ``ArticleAbstractSkel`` has the value from the
                value range of a scope bone in the :class:`DiscountConditionSkel`.

            -   The context (e.g. language) matches the value range of a scope bone.
        """
        ...

    @property
    def is_applicable(self) -> bool:
        """Cached and evaluated precondition"""
        if self._is_applicable is None:
            self._is_applicable = self.precondition()
        return self._is_applicable

    @property
    def is_fulfilled(self) -> bool:
        """Cached and evaluated condition"""
        if self._is_fulfilled is None and self.is_applicable:
            self._is_fulfilled = self()
        return self._is_fulfilled

    def __repr__(self) -> str:
        """Represent the scope as a string"""
        return (
            f'<{self.__class__.__name__} with '
            f'{self.is_applicable=} and {self.is_fulfilled=}>'
        )


class ConditionValidator:
    """
    Validator that validates a specific discount condition (with many scopes).

    It validates a complete :class:`DiscountConditionSkel`.
    """
    scopes: list[t.Type[DiscountConditionScope]] = []

    def __init__(self):
        super().__init__()
        self._is_fulfilled = None
        self.scope_instances: list[DiscountConditionScope] = []
        self.cart_skel = None
        self.article_skel = None
        self.discount_skel = None
        self.condition_skel = None
        self.context = None

    def __call__(
        self,
        *,
        cart_skel: SkeletonInstance_T["CartNodeSkel"] | None | Sentinel = SENTINEL,
        article_skel: SkeletonInstance_T["ArticleAbstractSkel"] | None | Sentinel = SENTINEL,
        discount_skel: SkeletonInstance_T["DiscountSkel"] | None | Sentinel = SENTINEL,
        code: str | None | Sentinel = SENTINEL,
        condition_skel: SkeletonInstance_T["DiscountConditionSkel"],
        context: DiscountValidationContext,
    ) -> t.Self:
        self.cart_skel = cart_skel
        self.discount_skel = discount_skel
        self.condition_skel = condition_skel
        self.code = code
        self.context = context

        for Scope in ConditionValidator.scopes:
            scope = Scope(
                cart_skel=cart_skel,
                article_skel=article_skel,
                discount_skel=discount_skel,
                condition_skel=condition_skel,
                code=code,
                context=context,
            )
            self.scope_instances.append(scope)
        # logger.debug(f"{self.scope_instances = }")
        return self

    @property
    def applicable_scopes(self) -> list[DiscountConditionScope]:
        return [
            scope for scope in self.scope_instances
            if scope.is_applicable and self.context in scope.allowed_contexts
        ]

    @property
    def is_fulfilled(self) -> bool:
        if self._is_fulfilled is None:
            self._is_fulfilled = all(scope.is_fulfilled for scope in self.applicable_scopes)
        return self._is_fulfilled

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} with {self.is_fulfilled=} "
            f"for {self.discount_skel=}, {_skel_repr(self.condition_skel)}, "
            f"cart_skel={_skel_repr(self.cart_skel)}, "
            f"article_skel={_skel_repr(self.article_skel)}"
            f"using {self.applicable_scopes=}>"
        )

    @classmethod
    def register(cls, scope: t.Type[DiscountConditionScope]):
        cls.scopes.append(scope)
        return scope


class DiscountValidator:
    """
    Validator that validates a specific discount (with many conditions).

    It validates a complete :class:`DiscountSkel`.
    """

    def __init__(self):
        super().__init__()
        self._is_fulfilled = None
        self.condition_validator_instances: list[ConditionValidator] = []
        self.cart_skel = None
        self.article_skel = None
        self.discount_skel = None
        self.condition_skels = []
        self.context = None

    def __call__(
        self,
        *,
        cart_skel: SkeletonInstance_T["CartNodeSkel"] | None | Sentinel = SENTINEL,
        article_skel: SkeletonInstance_T["ArticleAbstractSkel"] | None | Sentinel = SENTINEL,
        discount_skel: SkeletonInstance_T["DiscountSkel"] | None | Sentinel = SENTINEL,
        code: str | None | Sentinel = SENTINEL,
        context: DiscountValidationContext = SENTINEL,
    ) -> t.Self:
        self.cart_skel = cart_skel
        self.article_skel = article_skel
        self.discount_skel = discount_skel
        self.code = code
        self.context = context

        from ..skeletons import ArticleAbstractSkel

        # TODO: move this check in a generic version into viur-toolkit
        if (
            article_skel is not None
            and (not isinstance(article_skel, SkeletonInstance)
                 or not issubclass(article_skel.skeletonCls, ArticleAbstractSkel))
        ):
            okay = False
            # FIXME: RefSkelFor sucks: Why isn't a RefSkel subclassed from the source skel too
            if issubclass(article_skel.skeletonCls, RefSkel):
                full_skel_cls = skeletonByKind(article_skel.skeletonCls.kindName)
                if issubclass(full_skel_cls, ArticleAbstractSkel):
                    okay = True
            if not okay:
                raise TypeError(f"article_skel must be a SkeletonInstance for ArticleAbstractSkel. "
                                f"Got {article_skel.skeletonCls=}")

        # We need the full skel with all bones (otherwise the refSkel would be to large)
        for condition in discount_skel["condition"]:
            if not (condition_skel := SHOP_INSTANCE.get().discount_condition.get_skel(condition["dest"]["key"])):
                logger.warning(f'Broken relation {condition=} in {discount_skel["key"]}?!')
                raise InvalidStateError(f'Broken relation {condition=} in {discount_skel["key"]}?!')
                self.condition_skels.append(None)  # TODO
                self.condition_validator_instances.append(None)  # TODO
                continue
            cv = ConditionValidator()(
                cart_skel=cart_skel,
                article_skel=article_skel,
                discount_skel=discount_skel,
                condition_skel=condition_skel,
                code=code,
                context=context,
            )
            self.condition_skels.append(condition_skel)
            self.condition_validator_instances.append(cv)

        return self

    @property
    def is_fulfilled(self) -> bool:
        if self._is_fulfilled is None:
            if self.discount_skel["condition_operator"] == ConditionOperator.ONE_OF:
                logger.debug("Checking for any")
                self._is_fulfilled = any(cv.is_fulfilled for cv in self.condition_validator_instances)
            elif self.discount_skel["condition_operator"] == ConditionOperator.ALL:
                logger.debug("Checking for all")
                logger.debug(f"{self.condition_validator_instances=}")

                pprint.pprint(self.condition_validator_instances)
                self._is_fulfilled = all(cv.is_fulfilled for cv in self.condition_validator_instances)
            else:
                raise InvalidStateError(f'Invalid condition operator: {self.discount_skel["condition_operator"]}')
        return self._is_fulfilled

    @property
    def application_domain(self) -> ApplicationDomain:
        domains = {cm.condition_skel["application_domain"] for cm in self.condition_validator_instances}
        domains.discard(ApplicationDomain.ALL)
        if len(domains) > 1:
            raise NotImplementedError(f"Ambiguous application_domains: {domains=}")
        return domains.pop()

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} with {self.is_fulfilled=} "
            f"for {_skel_repr(self.discount_skel)}, "
            f"cart_skel={_skel_repr(self.cart_skel)}, "
            f"article_skel={_skel_repr(self.article_skel)}"
            f"using {self.condition_validator_instances=}>"
        )


@ConditionValidator.register
class ScopeCode(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["code_type"] in {CodeType.INDIVIDUAL, CodeType.INDIVIDUAL}
            # and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        if (
            self.condition_skel["code_type"] == CodeType.UNIVERSAL
            # and self.condition_skel["scope_code"] != self.code
        ):
            # logger.info(f'scope_code UNIVERSAL not reached ({self.condition_skel["scope_code"]=} != {self.code=})')
            logger.debug(f'scope_code {self.condition_skel["scope_code"]=} =?= {self.code=}')
            return self.condition_skel["scope_code"].lower() == self.code.lower()
        elif (
            self.condition_skel["code_type"] == CodeType.INDIVIDUAL
        ):
            sub = (
                SHOP_INSTANCE.get().discount_condition.viewSkel().all()
                .filter("parent_code.dest.__key__ =", self.condition_skel["key"])
                .getSkel()
            )
            logger.debug(f"{sub = }")
            if sub["quantity_used"] > 0:
                logger.info(f'code_type INDIVIDUAL not reached (sub already used)')
                return False
        return True


@ConditionValidator.register
class ScopeMinimumOrderValue(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_minimum_order_value"] is not None
            and (  # needs a context to verify
                self.article_skel is not None
                or (self.cart_skel is not None
                    and self.condition_skel["application_domain"] == ApplicationDomain.BASKET)
            )
        )

    def __call__(self) -> bool:
        if self.cart_skel is not None and self.condition_skel["application_domain"] == ApplicationDomain.BASKET:
            # In this case the discount should be applied on the basket.
            # FIXME: The wrapped sub-cart must be checked, not the entire cart.
            return self.condition_skel["scope_minimum_order_value"] <= self.cart_skel["total"]

        if self.article_skel is None:
            raise InvalidStateError("Missing context article")

        # In this case the discount should be applied only on a specific article,
        # the current article must have at least this price.
        # FIXME: nested discounts are not considered
        return self.condition_skel["scope_minimum_order_value"] <= self.article_skel["shop_price_retail"]


@ConditionValidator.register
class ScopeDateStart(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_date_start"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_start"] <= utils.utcNow()


@ConditionValidator.register
class ScopeDateStartPrevalidation(DiscountConditionScope):
    """
    Start date prevalidation for automatically discounts

    For prevalidation an offset of 7 days will be added,
    so entries that will be active soon are already in the cache,
    but entries in the distant future are filtered out.
    """

    allowed_contexts = [
        DiscountValidationContext.AUTOMATICALLY_PREVALIDATE,
    ]

    def precondition(self) -> bool:
        return self.condition_skel["scope_date_start"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_start"] <= utils.utcNow() + td(days=7)


@ConditionValidator.register
class ScopeDateEnd(DiscountConditionScope):
    prevalidate_for_automatically = True

    allowed_contexts: t.Final[list[DiscountValidationContext]] = [
        DiscountValidationContext.NORMAL,
        DiscountValidationContext.AUTOMATICALLY_PREVALIDATE,
        DiscountValidationContext.AUTOMATICALLY_LIVE,
    ]

    def precondition(self) -> bool:
        return self.condition_skel["scope_date_end"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_end"] >= utils.utcNow()


@ConditionValidator.register
class ScopeLanguage(DiscountConditionScope):
    def precondition(self) -> bool:
        return bool(self.condition_skel["scope_language"])

    def __call__(self) -> bool:
        return current.language.get() in self.condition_skel["scope_language"]


@ConditionValidator.register
class ScopeCountry(DiscountConditionScope):
    def precondition(self) -> bool:
        return bool(self.condition_skel["scope_country"])

    def __call__(self) -> bool:
        if (
            self.cart_skel is not None
            and self.cart_skel["shipping_address"] is not None
        ):
            return self.cart_skel["shipping_address"]["dest"]["country"] in self.condition_skel["scope_country"]

        try:
            use_country = HOOK_SERVICE.dispatch(Hook.CURRENT_COUNTRY)("article")
        except DispatchError:
            logger.info("NOTE: This error can be eliminated by providing "
                        "a `Hook.CURRENT_COUNTRY` customization.")
            return False
        return use_country in self.condition_skel["scope_country"]


@ConditionValidator.register
class ScopeMinimumQuantity(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_minimum_quantity"] is not None
            and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        return (
            self.condition_skel["scope_minimum_quantity"] <= self.cart_skel["total_quantity"]
        )


@ConditionValidator.register
class ScopeCustomerGroup(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_customer_group"] is not None
            and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        if self.condition_skel["scope_customer_group"] == CustomerGroup.ALL:
            return True
        if current.user.get() is None:
            return False
        orders = (
            SHOP_INSTANCE.get().order.viewSkel().all()
            .filter("customer.dest.__key__ =", current.user.get()["key"])
            .filter("is_ordered =", True)
            .count(2)
        )
        if self.condition_skel["scope_customer_group"] == CustomerGroup.FIRST_ORDER:
            return orders == 0
        elif self.condition_skel["scope_customer_group"] == CustomerGroup.FIRST_ORDER:
            return orders > 0
        raise NotImplementedError


@ConditionValidator.register
class ScopeCombinableLowPrice(DiscountConditionScope):
    def precondition(self) -> bool:
        # logger.debug(f"ScopeCombinableLowPrice :: {self.cart_skel=} | {self.article_skel=}")
        return (
            self.condition_skel["scope_combinable_low_price"] is not None
            and self.article_skel is not None
        )

    def __call__(self) -> bool:
        return not self.article_skel["shop_is_low_price"] or self.condition_skel["scope_combinable_low_price"]


@ConditionValidator.register
class ScopeArticle(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            bool(self.condition_skel["scope_article"])
            and (  # needs a context to verify
                self.article_skel is not None
                or (self.cart_skel is not None
                    and self.condition_skel["application_domain"] == ApplicationDomain.BASKET)
            )
        )

    def __call__(self) -> bool:
        if self.cart_skel is not None and self.condition_skel["application_domain"] == ApplicationDomain.BASKET:
            # In this case the discount should be applied on the basket,
            # the scope_article must be inside of it.
            leaf_skels = (
                SHOP_INSTANCE.get().cart.viewSkel("leaf").all()
                .filter("parentrepo =", self.cart_skel["key"])
                .filter(
                    "article.dest.__key__ IN",
                    [article["dest"]["key"] for article in self.condition_skel["scope_article"]]
                )
                .fetch()
            )
            # logger.debug(f"<{len(leaf_skels)}>{leaf_skels = }")
            return len(leaf_skels) > 0

        if self.article_skel is None:
            raise InvalidStateError("Missing context article")

        # In this case the discount should be applied only on specific articles,
        # the current article must be in scope_article.
        return any(
            self.article_skel["key"] == article["dest"]["key"]
            for article in self.condition_skel["scope_article"]
        )
