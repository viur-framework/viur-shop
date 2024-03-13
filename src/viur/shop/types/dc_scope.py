import abc
import typing as t  # noqa

from viur.core import current, utils
from ..globals import SENTINEL, SHOP_LOGGER

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
    ):
        self.cart_skel = cart_skel
        self.discount_skel = discount_skel
        self.condition_skel = condition_skel

    def precondition(self) -> bool:
        return True

    # @abc.abstractmethod
    # def is_satisfied(self) -> bool:
    #     ...

    @abc.abstractmethod
    def __call__(self) -> bool:
        # self.precondition_ = res = self.precondition()
        # if not res:
        #     return None
        # self.is_satisfied_ = res = self.is_satisfied()
        # return res
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


class ScopeManager:
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
    ) -> t.Self:
        self.cart_skel = cart_skel
        self.discount_skel = discount_skel
        self.condition_skel = condition_skel
        for Scope in ScopeManager.scopes:
            scope = Scope(
                cart_skel=cart_skel,
                discount_skel=discount_skel,
                condition_skel=condition_skel,
            )
            self.scope_instances.append(scope)
            # scope.validate()

        logger.debug(f"{self.scope_instances = }")
        return self

    @property
    def required_scopes(self) -> list[DiscountConditionScope]:
        return [scope for scope in self.scope_instances
                if scope.is_applicable]

    @property
    def is_fulfilled(self) -> bool:
        if self._is_fulfilled is None:
            self._is_fulfilled = all(scope.is_fulfilled for scope in self.required_scopes)
        return self._is_fulfilled

    def __repr__(self):
        return f"<{self.__class__.__name__} with {self.is_fulfilled=} for {self.discount_skel=}, {self.condition_skel=}, {self.cart_skel=} using {self.required_scopes=}>"


class ScopeOrderValue(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_minimum_order_value"] is not None
            and self.cart_skel is not None
        )

    def __call__(self) -> bool:
        return (
           self.condition_skel["scope_minimum_order_value"] <= self.cart_skel["total"]
        )


ScopeManager.scopes.append(ScopeOrderValue)


class ScopeMinimumQuantity(DiscountConditionScope):
    def precondition(self) -> bool:
        return (
            self.condition_skel["scope_minimum_quantity"] is not None
            and     self.cart_skel is not None
        )

    def __call__(self) -> bool:
        return (
                self.condition_skel["scope_minimum_quantity"] <= self.cart_skel["total_quantity"]
        )


ScopeManager.scopes.append(ScopeMinimumQuantity)


class ScopeLanguage(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_language"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_language"] == current.language.get()


ScopeManager.scopes.append(ScopeLanguage)


class ScopeDateStart(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_date_start"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_start"] <= utils.utcNow()


ScopeManager.scopes.append(ScopeDateStart)


class ScopeDateEnd(DiscountConditionScope):
    def precondition(self) -> bool:
        return self.condition_skel["scope_date_end"] is not None

    def __call__(self) -> bool:
        return self.condition_skel["scope_date_end"] >= utils.utcNow()


ScopeManager.scopes.append(ScopeDateEnd)
