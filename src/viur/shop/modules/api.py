import typing as t  # noqa

from google.protobuf.message import DecodeError
from viur.core import current, db, errors, exposed, force_post
from viur.core.render.json.default import DefaultRender as JsonRenderer

import viur.shop.types.exceptions as e
from viur.shop.modules.abstract import ShopModuleAbstract
from viur.shop.skeletons import ShippingSkel
from viur.shop.types import *
from ..globals import SENTINEL, SHOP_INSTANCE_VI, SHOP_LOGGER

if t.TYPE_CHECKING:
    from viur.shop import OrderSkel, SkeletonInstance_T

logger = SHOP_LOGGER.getChild(__name__)


# TODO: add methods
# TODO: add permission concept

class Api(ShopModuleAbstract):

    @property
    def json_renderer(self) -> JsonRenderer:
        return SHOP_INSTANCE_VI.get().render

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
        quantity: int = 1,
        quantity_mode: QuantityModeType = "replace",
        parent_cart_key: str | db.Key,
    ):
        """Add an article to the cart"""
        article_key = self._normalize_external_key(
            article_key, "article_key")
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        try:
            quantity_mode = QuantityMode(quantity_mode)
        except ValueError:
            raise e.InvalidArgumentException("quantity_mode", quantity_mode)
        # TODO: Could also return self.article_view() or just the cart_node_key...
        return JsonResponse(self.shop.cart.add_or_update_article(
            article_key, parent_cart_key, quantity, quantity_mode))

    @exposed
    @force_post
    def article_update(
        self,
        *,
        article_key: str | db.Key,
        quantity: int,
        quantity_mode: QuantityModeType = "replace",
        parent_cart_key: str | db.Key,
    ):
        """Update an existing article in the cart"""
        article_key = self._normalize_external_key(
            article_key, "article_key")
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        try:
            quantity_mode = QuantityMode(quantity_mode)
        except ValueError:
            raise e.InvalidArgumentException("quantity_mode", quantity_mode)
        if not self.shop.cart.get_article(article_key, parent_cart_key):
            raise errors.NotFound(f"{parent_cart_key} has no article with {article_key=}")
        # TODO: Could also return self.article_view() or just the cart_node_key...
        return JsonResponse(self.shop.cart.add_or_update_article(
            article_key, parent_cart_key, quantity, quantity_mode))

    @exposed
    @force_post
    def article_remove(
        self,
        *,
        article_key: str | db.Key,
        parent_cart_key: str | db.Key,
    ):
        """Remove an article from the cart"""
        return self.article_update(
            article_key=article_key, quantity=0, parent_cart_key=parent_cart_key)

    @exposed
    @force_post
    def article_move(
        self,
        *,
        article_key: str | db.Key,
        parent_cart_key: str | db.Key,
        new_parent_cart_key: str | db.Key,
    ):
        """Move an article inside a cart"""
        article_key = self._normalize_external_key(
            article_key, "article_key")
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        new_parent_cart_key = self._normalize_external_key(
            new_parent_cart_key, "new_parent_cart_key")
        return JsonResponse(self.shop.cart.article_move(
            article_key, parent_cart_key, new_parent_cart_key))

    @exposed
    @force_post
    def cart_add(
        self,
        *,
        parent_cart_key: str | db.Key = None,
        cart_type: CartType = None,  # TODO: since we generate basket automatically,
        #                                    wishlist would be the only acceptable value ...
        name: str = None,
        customer_comment: str = None,
        shipping_address_key: str | db.Key = None,
        shipping_key: str | db.Key = None,
        discount_key: str | db.Key = None,
    ):
        """
        Add a new cart node

        :param parent_cart_key: Key of the parent cart
        :param cart_type: Type of the cart node, see :class:`CartType`
        :param name: Optional. Name of the cart node
        :param customer_comment: Optional. Comment to this node, by customer.
        :param shipping_address_key: Optional. Key of the address
        :param shipping_key: Optional. Key of the shipping
        :param discount_key: Optional. Key of the discount

        Returns: The created cart node skel
        """
        parent_cart_key = self._normalize_external_key(
            parent_cart_key, "parent_cart_key")
        shipping_address_key = self._normalize_external_key(
            shipping_address_key, "shipping_address_key", True)
        shipping_key = self._normalize_external_key(
            shipping_key, "shipping_key", True)
        discount_key = self._normalize_external_key(
            discount_key, "discount_key", True)
        if cart_type is not None:
            try:
                cart_type = CartType(cart_type)
            except ValueError:
                raise e.InvalidArgumentException("cart_type", cart_type)
        return JsonResponse(self.shop.cart.cart_add(
            parent_cart_key=parent_cart_key,
            cart_type=cart_type,
            name=name,
            customer_comment=customer_comment,
            shipping_address_key=shipping_address_key,
            shipping_key=shipping_key,
            discount_key=discount_key,
        ))

    @exposed
    @force_post
    def cart_update(
        self,
        *,
        cart_key: str | db.Key,
        cart_type: CartType = None,  # TODO: necessary?
        name: str = None,
        customer_comment: str = None,
        shipping_address_key: str | db.Key = None,
        shipping_key: str | db.Key = None,
        discount_key: str | db.Key = None,  # TODO: use sentinel?
    ):
        """
        Update an existing cart node

        :param cart_key: Key of the cart node to be updated
        :param cart_type: Type of the cart node, see :class:`CartType`
        :param name: Optional. Name of the cart node
        :param customer_comment: Optional. Comment to this node, by customer.
        :param shipping_address_key: Optional. Key of the address
        :param shipping_key: Optional. Key of the shipping
        :param discount_key: Optional. Key of the discount

        Returns: The updated cart node skel
        """
        cart_key = self._normalize_external_key(
            cart_key, "parent_cart_key")
        shipping_address_key = self._normalize_external_key(
            shipping_address_key, "shipping_address_key", True)
        shipping_key = self._normalize_external_key(
            shipping_key, "shipping_key", True)
        discount_key = self._normalize_external_key(
            discount_key, "discount_key", True)
        return JsonResponse(self.shop.cart.cart_update(
            cart_key=cart_key,
            cart_type=cart_type,
            name=name,
            customer_comment=customer_comment,
            shipping_address_key=shipping_address_key,
            shipping_key=shipping_key,
            discount_key=discount_key,
        ))

    @exposed
    @force_post
    def cart_remove(
        self,
        *,
        cart_key: str | db.Key,
    ):
        """
        Remove a cart node.

        Removes itself and all children
        :param cart_key: Key of the cart node to be removed
        """
        cart_key = self._normalize_external_key(cart_key, "cart_key")
        return JsonResponse(self.shop.cart.cart_remove(cart_key))

    @exposed
    @force_post
    def cart_clear(
        self,
        *,
        cart_key: str | db.Key,
        remove_sub_carts: bool = False,
    ):
        """Remove direct or all children

        :param remove_sub_carts: Remove child leafs, keep nodes
        """
        cart_key = self._normalize_external_key(cart_key, "cart_key")
        ...

    @exposed
    def basket_list(
        self,
    ):
        """List the children of the basket (the cart stored in the session)"""
        return self.cart_list(cart_key=self.shop.cart.current_session_cart_key)

    @exposed
    def basket_view(
        self,
    ):
        """View the basket (the cart stored in the session) itself"""
        return self.shop.cart.view(key=self.shop.cart.current_session_cart_key, skelType="node")

    @exposed
    def cart_list(
        self,
        cart_key: str | db.Key | None = None,
    ):
        """
        List root nodes or children of a cart

        If a cart key is provided, the direct children (nodes and leafs) will
        be returned.
        Otherwise (without a key), the root nodes will be returned.

        :param cart_key: list direct children (nodes and leafs) of this parent node
        """
        # no key: list root node
        if cart_key is None:
            return JsonResponse(self.shop.cart.getAvailableRootNodes())
        # key provided: list children (nodes and leafs)
        cart_key = self._normalize_external_key(cart_key, "cart_key")
        children = []
        for child_skel in self.shop.cart.get_children(cart_key):
            assert issubclass(child_skel.skeletonCls, (self.shop.cart.nodeSkelCls, self.shop.cart.leafSkelCls))
            child = self.json_renderer.renderSkelValues(child_skel)
            # if issubclass(child_skel.skeletonCls, self.shop.cart.leafSkelCls):
            #     logger.debug(f'{child_skel = }')
            #     logger.debug(f'{child_skel["price"] = }')
            #     logger.debug(f'{child_skel.price = }')
            #     logger.debug(f'{child_skel.price.compute = }')
            #     logger.debug(f'{child_skel.accessedValues = }')
            child["skel_type"] = "leaf" if issubclass(child_skel.skeletonCls, self.shop.cart.leafSkelCls) else "node"
            children.append(child)
        return JsonResponse(children)

    @exposed
    @force_post
    def order_add(
        self,
        *,
        cart_key: str | db.Key,
        payment_provider: str = SENTINEL,
        billing_address_key: str | db.Key = SENTINEL,
        email: str = SENTINEL,
        customer_key: str | db.Key = SENTINEL,
        state_ordered: bool = SENTINEL,
        state_paid: bool = SENTINEL,
        state_rts: bool = SENTINEL,
    ):
        cart_key = self._normalize_external_key(cart_key, "cart_key")
        billing_address_key = self._normalize_external_key(billing_address_key, "billing_address_key", True)
        customer_key = self._normalize_external_key(customer_key, "customer_key", True)
        ...
        return JsonResponse(self.shop.order.order_add(
            cart_key, payment_provider, billing_address_key,
            email, customer_key, state_ordered, state_paid, state_rts))

    @exposed
    @force_post
    def order_update(
        self,
        *,
        order_key: str | db.Key,
        payment_provider: str = SENTINEL,
        billing_address_key: str | db.Key = SENTINEL,
        email: str = SENTINEL,
        customer_key: str | db.Key = SENTINEL,
        state_ordered: bool = SENTINEL,
        state_paid: bool = SENTINEL,
        state_rts: bool = SENTINEL,
    ):
        order_key = self._normalize_external_key(order_key, "order_key")
        billing_address_key = self._normalize_external_key(billing_address_key, "billing_address_key", True)
        customer_key = self._normalize_external_key(customer_key, "customer_key", True)
        return JsonResponse(self.shop.order.order_update(
            order_key, payment_provider, billing_address_key,
            email, customer_key, state_ordered, state_paid, state_rts))

    @exposed
    @force_post
    def order_remove(
        self,
        *,
        order_key: str | db.Key,
    ):
        ...

    @exposed
    def order_list(
        self,
        **kwargs,
    ) -> JsonResponse[list[OrderViewResult]]:
        """List the orders of the current user"""
        query: db.Query = self.shop.order.viewSkel().all()
        if user := current.user.get():
            query.filter("customer.dest.__key__ =", user["key"])
        elif self.shop.order.current_session_order_key:
            query.mergeExternalFilter({"key": self.shop.order.current_session_order_key})
        else:
            return JsonResponse([])
        query.mergeExternalFilter(kwargs)  # Allow more filtering, cursor, amount, ...
        return JsonResponse([
            self._get_order_view_result(skel) for skel in query.fetch()
        ])

    @exposed
    def order_view(
        self,
        order_key: str | db.Key | t.Literal["SESSION"] = "SESSION",
    ) -> JsonResponse[OrderViewResult]:
        """
        View an order

        :param order_key: Key of the order to view. Use "SESSION" as key to view the order of the current session
        """
        if order_key == "SESSION":
            if not self.shop.order.current_session_order_key:
                raise errors.PreconditionFailed(
                    "There is no order in the current session"
                )
            order_key = self.shop.order.current_session_order_key
        else:
            order_key = self._normalize_external_key(order_key, "order_key")  # noqa: type

        if (skel := self.shop.order.order_get(order_key)) is None:
            raise errors.NotFound("Order not found")

        return JsonResponse(self._get_order_view_result(skel))

    def _get_order_view_result(
        self,
        order_skel: SkeletonInstance_T["OrderSkel"],
    ) -> OrderViewResult:
        return {
            "skel": order_skel,
            "can_order": {
                "status": not bool(can_order_errors := self.shop.order.can_order(order_skel)),
                "errors": can_order_errors,
            },
            "can_checkout": {
                "status": not bool(can_checkout_errors := self.shop.order.can_checkout(order_skel)),
                "errors": can_checkout_errors,
            },
        }

    @exposed
    @force_post
    def discount_add(
        self,
        *,
        code: str = None,
        discount_key: str | db.Key = None,
        # TODO: Use always session key? parent_cart_key: str | db.Key,
    ):
        """
        parameter code xor discount_key: str | db.Key

        Sucht nach Rabatt mit dem code xor key, je nach Typ (Artikel/Warenkorb) suche ...ende parent_node oder erzeuge eine und setze dort die discount Relation.
        """
        discount_key = self._normalize_external_key(discount_key, "discount_key", True)
        return JsonResponse(self.shop.discount.apply(code, discount_key))

    @exposed
    @force_post
    def discount_remove(
        self,
        *,
        discount_key: str | db.Key,
    ):
        discount_key = self._normalize_external_key(discount_key, "discount_key")
        return JsonResponse(self.shop.discount.remove(discount_key))

    @exposed
    def shipping_list(
        self,
        cart_key: str | db.Key,
    ) -> JsonResponse[list[SkeletonInstance_T[ShippingSkel]]]:
        """
        Lists available shipping options for a (sub)cart

        :param cart_key: Key of the parent cart

        :returns: list of :class:`ShippingSkel` `SkeletonInstance`s
        """
        cart_key = self._normalize_external_key(cart_key, "cart_key")
        return JsonResponse(self.shop.shipping.get_shipping_skels_for_cart(cart_key))

    # --- Internal helpers  ----------------------------------------------------

    def _normalize_external_key(
        self,
        external_key: str,
        parameter_name: str,
        can_be_None: bool = False,
    ) -> db.Key | None:
        """
        Convert urlsafe key to db.Key and raise an error on invalid in key.
        """
        if can_be_None and external_key is SENTINEL:
            return SENTINEL
        if can_be_None and not external_key:
            return None
        elif not external_key:
            raise InvalidKeyException(external_key, parameter_name)
        try:
            return db.Key.from_legacy_urlsafe(external_key)
        except (ValueError, DecodeError):  # yes, the exception really comes from protobuf...
            raise InvalidKeyException(external_key, parameter_name)


Api.html = True
Api.vi = True
