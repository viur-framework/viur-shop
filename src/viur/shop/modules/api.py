import logging

from viur.core import exposed
from viur.shop.modules.abstract import ShopModuleAbstract

logger = logging.getLogger("viur.shop").getChild(__name__)


# TODO: add methods
# TODO: add permission concept


class Api(ShopModuleAbstract):

    @exposed
    def article_view(self, article_key: str, parent_cart_key: str):
        ...

    @exposed
    def tmp_article_list(self):  # TODO testing only
        return [
            skel["shop_name"]
            for skel in self.shop.article_skel().all().fetch()
        ]

    @exposed
    def tmp_article_gen(self):  # TODO testing only
        for i in range(10):
            skel = self.shop.article_skel()
            skel["shop_name"] = f"Article #{str(i).zfill(5)}"
            skel.toDB()
            logger.info(f"Added article skel {skel}")


Api.html = True
Api.vi = True
