import functools

from viur.core.prototypes import List
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER
from ..services import HOOK_SERVICE, Hook
from ..types import VatRateCategory
from ..types.exceptions import ConfigurationError

logger = SHOP_LOGGER.getChild(__name__)


class VatRate(ShopModuleAbstract, List):
    moduleName = "vat_rate"
    kindName = "{{viur_shop_modulename}}_vat_rate"

    # default_order = ("country", db.SortOrder.Ascending)

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "cash-stack"
        return admin_info

    @functools.cached_property
    def vat_rates(self):
        """Cache the vat rates

        Since this configuration will not change much,
        we cache the whole thing persistently within the instance.
        So after changing the VAT rates, the instance would have to be
        restarted -- or someone would have to create a pull request
        with an alternative solution.
        """
        return {
            skel["country"]: {
                cfg["category"]: cfg["percentage"]
                for cfg in skel["configuration"]
            }
            for skel in self.viewSkel().all().fetch(100)
        }

    @functools.cached_property
    def _vat_skel(self):
        return self.viewSkel()

    def get_vat_rate_for_country(
        self,
        *,
        country: str | None = None,
        category: VatRateCategory,
    ) -> float:
        """Get the configured vat rate percentage for a country."""
        if not isinstance(category, VatRateCategory):
            raise TypeError(f"{category!r} is not a VatRateCategory")
        if country is None:
            country = HOOK_SERVICE.dispatch(Hook.CURRENT_COUNTRY)("vat_rate")
        if country not in self._vat_skel.country.values:
            raise ValueError(f"Invalid country code {country}")
        if country not in self.vat_rates:
            raise ConfigurationError(f"VatRate Skeleton missing for {country=}")
        try:
            return self.vat_rates[country][category]
        except KeyError:
            if category == VatRateCategory.ZERO:
                return 0.0
            raise ConfigurationError(f"VatRate configuration missing for {country=} and {category=}")
