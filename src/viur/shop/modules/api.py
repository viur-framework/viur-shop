import logging

from google.protobuf.message import DecodeError

from viur.core import db, errors, exposed, force_post
from viur.shop.constants import CartType
from viur.shop.exceptions import InvalidKeyException
from viur.shop.modules.abstract import ShopModuleAbstract
from viur.shop.response_types import JsonResponse

logger = logging.getLogger("viur.shop").getChild(__name__)


# TODO: add methods
# TODO: add permission concept
# TODO: add @force_post to not-view methods


class Api(ShopModuleAbstract):

    @exposed
    def article_view(
        self,
        article_key: str | db.Key,
        parent_cart_key: str | db.Key,
    ):
        """View an article in the cart"""
        article_key = self._normalize_external_key(
            article_key, "article_key")
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        if not (res := self.shop.cart.get_article(article_key, parent_cart_key)):
            raise errors.NotFound(f"{parent_cart_key} has no article with {article_key=}")
        return JsonResponse(res)

    @exposed
    @force_post
    def article_add(
        self,
        *,
        article_key: str | db.Key,
        quantity: int,
        parent_cart_key: str | db.Key,
    ):
        """Add an article to the cart"""
        article_key = self._normalize_external_key(
            article_key, "article_key")
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        # TODO: Could also return self.article_view() or just the cart_node_key...
        if self.shop.cart.get_article(article_key, parent_cart_key):
            raise errors.BadRequest("Article already exists")
        return JsonResponse(self.shop.cart.add_or_update_article(
            article_key, parent_cart_key, quantity))

    @exposed
    @force_post
    def article_update(
        self,
        *,
        article_key: str | db.Key,
        quantity: int,
        parent_cart_key: str | db.Key,
    ):
        """Update an existing article in the cart"""
        article_key = self._normalize_external_key(
            article_key, "article_key")
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        if not self.shop.cart.get_article(article_key, parent_cart_key):
            raise errors.BadRequest("Article does not exist")
        # TODO: Could also return self.article_view() or just the cart_node_key...
        return JsonResponse(self.shop.cart.add_or_update_article(
            article_key, parent_cart_key, quantity))

    @exposed
    @force_post
    def article_remove(
        self,
        *,
        article_key: str | db.Key,
        parent_cart_key: str | db.Key,
    ):
        """Remove an article from the cart"""
        return self.article_update(article_key, 0, parent_cart_key)

    @exposed
    def article_move(
        self,
        *,
        article_key: str | db.Key,
        parent_cart_key: str | db.Key,
        new_parent_cart_key: str | db.Key,
    ):
        ...

    @exposed
    def cart_add(
        self,
        *,
        parent_cart_key: str | db.Key = None,
        cart_type: CartType,
        name: str = None,
        customer_comment: str = None,
        shipping_address_key: str | db.Key = None,
        shipping_key: str | db.Key = None,
    ):
        ...

    @exposed
    def cart_update(
        self,
        *,
        cart_key: str | db.Key,
        name: str = None,
        customer_comment: str = None,
        shipping_address_key: str | db.Key = None,
        shipping_key: str | db.Key = None,
    ):
        ...

    @exposed
    def cart_remove(
        self,
        *,
        cart_key: str | db.Key,
    ):
        ...

    @exposed
    def cart_clear(
        self,
        *,
        cart_key: str | db.Key,
        remove_sub_carts: bool = False,
    ):
        ...

    @exposed
    def cart_list(
        self,
        cart_key: str | db.Key | None = None,
    ):
        """
        kein cart_key: Listet root-nodes auf

        cart_key: listet direkte Kinder (leafs und nodes) auf
        """
        if cart_key is None:
            return JsonResponse(self.shop.cart.getAvailableRootNodes())
        raise errors.NotImplemented

    @exposed
    @force_post
    def order_add(
        self,
        *,
        order_key: str | db.Key,
        payment_provider: str = None,
        billing_address_key: str | db.Key = None,
        email: str = None,
        customer_key: str | db.Key = None,
        state_ordered: bool = None,
        state_paid: bool = None,
        state_rts: bool = None,
    ):
        ...

    @exposed
    def order_update(
        self,
        *,
        order_key: str | db.Key,
        payment_provider: str = None,
        billing_address_key: str | db.Key = None,
        email: str = None,
        customer_key: str | db.Key = None,
        state_ordered: bool = None,
        state_paid: bool = None,
        state_rts: bool = None,
    ):
        ...

    @exposed
    def order_remove(
        self,
        *,
        order_key: str | db.Key,
    ):
        ...

    @exposed
    def order_view(
        self,
        order_key: str | db.Key,
    ):
        """
        Gibt gesetzte Werte (BillAddress) aus und gibt computed Wert "is_orderable" aus,
        ob alle Vorbedingungen für Bestellabschluss erfüllt sind.
        """
        ...

    @exposed
    def discount_add(
        self,
        *,
        code: str,
        discount_key: str | db.Key,
    ):
        """
        parameter code xor discount_key: str | db.Key

        Sucht nach Rabatt mit dem code xor key, je nach Typ (Artikel/Warenkorb) suche ...ende parent_node oder erzeuge eine und setze dort die discount Relation.
        """
        ...

    @exposed
    def discount_remove(
        self,
        *,

        discount_key: str | db.Key,
    ):
        ...

    @exposed
    def shipping_list(
        self,
        cart_key: str | db.Key,
    ):
        """
        Listet verfügbar Versandoptionen für einen (Unter)Warenkorb auf
        """
        ...

    # --- Internal helpers  ----------------------------------------------------

    def _normalize_external_key(
        self,
        external_key: str,
        parameter_name: str,
    ) -> db.Key:
        """
        Convert urlsafe key to db.Key and raise an error on invalid in key.
        """
        try:
            return db.Key.from_legacy_urlsafe(external_key)
        except DecodeError:  # yes, the exception really comes from protobuf...
            raise InvalidKeyException(external_key, parameter_name)

    # --- Testing only --------------------------------------------------------

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
