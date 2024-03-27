import abc
import pprint
import typing as t  # noqa

from viur.core import current, utils
from viur.core.skeleton import Skeleton, SkeletonInstance, skeletonByKind
from ..globals import SENTINEL, SHOP_INSTANCE, SHOP_LOGGER
from ..types import *

logger = SHOP_LOGGER.getChild(__name__)


class DiscountConditionScope:
    _is_applicable = None
    _is_fulfilled = None

    def __init__(
        self,
        *,
        cart_skel=SENTINEL,
        discount_skel=SENTINEL,
        condition_skel=SENTINEL,
        code=SENTINEL,
    ):
        self.cart_skel = cart_skel
        self.discount_skel = discount_skel
        self.condition_skel = condition_skel
        self.code = code

    def precondition(self) -> bool:
        return True

    @abc.abstractmethod
    def __call__(self) -> bool:
        ...

    @property
    def is_applicable(self) -> bool:
        if self._is_applicable is None:
            self._is_applicable = self.precondition()
        return self._is_applicable

    @property
    def is_fulfilled(self) -> bool:
        if self._is_fulfilled is None and self.is_applicable:
            self._is_fulfilled = self()
        return self._is_fulfilled

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} with '
            f'{self.is_applicable=} and {self.is_fulfilled=}>'
        )


class ConditionValidator:
    scopes: list[t.Type[DiscountConditionScope]] = []

    def __init__(self):
        super().__init__()
        self._is_fulfilled = None
        self.scope_instances = []
        self.cart_skel = None
        self.discount_skel = None
        self.condition_skel = None

    def __call__(
        self,
        *,
        cart_skel=SENTINEL,
        discount_skel=SENTINEL,
        condition_skel=SENTINEL,
        code=SENTINEL,
    ) -> t.Self:
        self.cart_skel = cart_skel
        self.discount_skel = discount_skel
        self.condition_skel = condition_skel
        self.code = code
        for Scope in ConditionValidator.scopes:
            scope = Scope(
                cart_skel=cart_skel,
                discount_skel=discount_skel,
                condition_skel=condition_skel,
                code=code,
            )
            self.scope_instances.append(scope)
        # logger.debug(f"{self.scope_instances = }")
        return self

    @property
    def applicable_scopes(self) -> list[DiscountConditionScope]:
        return [scope for scope in self.scope_instances
                if scope.is_applicable]

    @property
    def is_fulfilled(self) -> bool:
        if self._is_fulfilled is None:
            self._is_fulfilled = all(scope.is_fulfilled for scope in self.applicable_scopes)
        return self._is_fulfilled

    def __repr__(self):
        return f"<{self.__class__.__name__} with {self.is_fulfilled=} for {self.condition_skel=} using {self.applicable_scopes=}>"
        return f"<{self.__class__.__name__} with {self.is_fulfilled=} for {self.discount_skel=}, {self.condition_skel=}, {self.cart_skel=} using {self.applicable_scopes=}>"

    @classmethod
    def register(cls, scope: t.Type[DiscountConditionScope]):
        cls.scopes.append(scope)
        return scope


class DiscountValidator:

    def __init__(self):
        super().__init__()
        self._is_fulfilled = None
        self.condition_validator_instances: list[ConditionValidator] = []
        self.cart_skel = None
        self.discount_skel = None
        self.condition_skels = []

    def __call__(
        self,
        *,
        cart_skel=SENTINEL,
        discount_skel=SENTINEL,
        code=SENTINEL,
    ) -> t.Self:
        self.cart_skel = cart_skel
        self.discount_skel = discount_skel
        self.code = discount_skel

        # We need the full skel with all bones (otherwise the refSkel would be to large)
        condition_skel_cls: t.Type[Skeleton] = skeletonByKind(discount_skel.condition.kind)
        for condition in discount_skel["condition"]:
            condition_skel: SkeletonInstance = condition_skel_cls()  # noqa
            if not condition_skel.fromDB(condition["dest"]["key"]):
                logger.warning(f'Broken relation {condition=} in {discount_skel["key"]}?!')
                raise InvalidStateError(f'Broken relation {condition=} in {discount_skel["key"]}?!')
                self.condition_skels.append(None)  # TODO
                self.condition_validator_instances.append(None)  # TODO
                continue
            cv = ConditionValidator()(cart_skel=cart_skel, discount_skel=discount_skel, condition_skel=condition_skel,
                                      code=code)
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
                # pprint.pprint(self.condition_validator_instances)
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
        return f"<{self.__class__.__name__} with {self.is_fulfilled=} for {self.discount_skel=}, {self.cart_skel=} using {self.condition_validator_instances=}>"


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
            return self.condition_skel["scope_code"] == self.code
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
            and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        return (
            self.condition_skel["scope_minimum_order_value"] <= self.cart_skel["total"]
        )


@ConditionValidator.register
class ScopeDateStart(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_date_start"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_start"] <= utils.utcNow()


@ConditionValidator.register
class ScopeDateEnd(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_date_end"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_end"] >= utils.utcNow()


@ConditionValidator.register
class ScopeLanguage(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_language"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_language"] == current.language.get()


@ConditionValidator.register
class ScopeCountry(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_country"] is not None
            and self.cart_skel is not None
            and self.cart_skel["shipping_address"] is not None
        )

    def __call__(self) -> bool:
        return self.condition_skel["scope_country"] == self.cart_skel["shipping_address"]["dest"]["country"]


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
        if current.user.get() is None:
            return False
        if self.condition_skel["scope_customer_group"] == CustomerGroup.ALL:
            return True
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


# @ConditionValidator.register TODO
class ScopeCombinableLowPrice(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_combinable_low_price"] is not None
            # and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        article_skel = ...  # FIXME: how we get this?
        return not article_skel["shop_is_low_price"] or self.condition_skel["scope_combinable_low_price"]


@ConditionValidator.register
class ScopeArticle(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_article"] is not None
            # and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        leaf_skels = (
            SHOP_INSTANCE.get().cart.viewSkel("leaf").all()
            .filter("parentrepo =", self.cart_skel["key"])
            .filter("article.dest.__key__ =", self.condition_skel["scope_article"]["dest"]["key"])
            .fetch()
        )
        logger.debug(f"<{len(leaf_skels)}>{leaf_skels = }")
        return len(leaf_skels) > 0
