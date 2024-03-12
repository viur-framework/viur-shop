import typing as t

from viur.core import current, errors, exposed
from viur.core.skeleton import SkeletonInstance
from . import PaymentProviderAbstract
from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class AmazonPay(PaymentProviderAbstract):
    name = "amazonpay"

    def __init__(
        self,
        *,
        mws_access_key: str,
        mws_secret_key: str,
        merchant_id: str,
        client_id: str,
        client_secret: str,
        region: str = "de",
        currency_code: str = "EUR",
        sandbox: bool = False,
        language: str = "en",
    ):
        super().__init__()
        self.mws_access_key = mws_access_key
        self.mws_secret_key = mws_secret_key
        self.merchant_id = merchant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.language = language

    def checkout(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        raise errors.NotImplemented()

    def get_checkout_start_data(
        self,
        order_skel: SkeletonInstance,
    ) -> t.Any:
        host = current.request.get().request.host_url
        return_url = f'{host.rstrip("/")}/{self.modulePath.strip("/")}/return_handler?order_key={order_skel["key"].to_legacy_urlsafe().decode("ASCII")}'
        return {
            "merchant_id": self.merchant_id,
            "client_id": self.client_id,
            "redirect_url": return_url,
            "sandbox": self.sandbox,
        }

    def charge(self):
        raise errors.NotImplemented()

    def check_payment_state(
        self,
        order_skel: SkeletonInstance,
    ) -> tuple[bool, t.Any]:
        raise errors.NotImplemented()

    @exposed
    def return_handler(self):
        raise errors.NotImplemented()

    @exposed
    def webhook(self):
        raise errors.NotImplemented()

    @exposed
    def get_debug_information(self):
        raise errors.NotImplemented()
