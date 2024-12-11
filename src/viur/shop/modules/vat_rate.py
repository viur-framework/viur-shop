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

    @functools.lru_cache(maxsize=None)
    def get_vat_rate_for_country(
        self,
        *,
        country: str | None = None,
        category: VatRateCategory,
    ) -> float:
        """Get the configured vat rate percentage for a country."""
        if country is None:
            country = HOOK_SERVICE.dispatch(Hook.CURRENT_COUNTRY)("vat_rate")
        skel = self.viewSkel()
        if country not in skel.country.values:
            raise ValueError(f"Invalid country code {country}")
        if not (skel := skel.all().filter("country =", country).getSkel()):
            raise ConfigurationError(f"VatRate Skeleton missing for {country=}")
        for configuration in skel["configuration"]:
            if configuration["category"] == category:
                return configuration["percentage"]
        if category == VatRateCategory.ZERO:
            return 0.0
        raise ConfigurationError(f"VatRate configuration missing for {country=} and {category=}")
