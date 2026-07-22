import typing as t  # noqa

import viur.shop.types.exceptions as e
from viur import toolkit
from viur.core import conf, current, db, errors, exposed, translate
from viur.core.bones import BaseBone, RelationalConsistency
from viur.core.prototypes import Tree
from viur.core.prototypes.tree import SkelType
from viur.core.session import Session
from viur.core.skeleton import Skeleton, SkeletonInstance
from viur.shop.modules.abstract import ShopModuleAbstract
from viur.shop.types import *
from ..globals import MAX_FETCH_LIMIT, SENTINEL, SHOP_INSTANCE, SHOP_LOGGER
from ..services import EVENT_SERVICE, Event
from ..skeletons.article import ArticleAbstractSkel
from ..skeletons.cart import CartItemSkel, CartNodeSkel
from ..types.response import make_json_dumpable

logger = SHOP_LOGGER.getChild(__name__)

if conf.version >= (3, 8, 16):
    from viur.core.skeleton.utils import without_render_preparation
else:
    from viur.toolkit import without_render_preparation


class Cart(ShopModuleAbstract, Tree):
    moduleName = "cart"
    nodeSkelCls = CartNodeSkel
    leafSkelCls = CartItemSkel

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "cart3"
        return admin_info

    # --- ViUR ----------------------------------------------------------------

    def baseSkel(
        self,
        skelType: SkelType,
        sub_skel: str | list[str] | None = None,
        *args, **kwargs
    ) -> SkeletonInstance:
        """Extend default baseSkel() by sub_skel parameter"""
        cls: t.Type[Skeleton] = self._resolveSkelCls(skelType, *args, **kwargs)
        if sub_skel is None:
            return cls()  # noqa
        if isinstance(sub_skel, list):
            return cls.subskel(*sub_skel)
        else:
            return cls.subskel(sub_skel)

    def canView(self, skelType: SkelType, skel: SkeletonInstance) -> bool:
        if super().canView(skelType, skel):
            return True
        if skelType == "leaf":
            nearest_node_key = skel["parententry"]
        else:
            assert skelType == "node"
            nearest_node_key = skel["key"]
        return self.is_valid_node(nearest_node_key)

    # --- Session -------------------------------------------------------------

    @property
    def current_session_cart_key(self) -> db.Key | None:
        return self.get_current_session_cart_key(create_if_missing=False)

    def get_current_session_cart_key(self, *, create_if_missing: bool = False) -> db.Key | None:
        if user := current.user.get():
            user_skel = conf.main_app.vi.user.viewSkel()
            user_skel.read(user["key"])
            if user_skel["basket"]:
                self.session["session_cart_key"] = user_skel["basket"]["dest"]["key"]
                current.session.get().markChanged()
        if create_if_missing:
            self._ensure_current_session_cart()
        return self.session.get("session_cart_key")

    @property
    def current_session_cart(self) -> SkeletonInstance_T[CartNodeSkel]:  # TODO: Caching
        skel = self.viewSkel("node")
        if not skel.read(self.get_current_session_cart_key(create_if_missing=True)):
            logger.critical(f"Invalid session_cart_key {self.current_session_cart_key} ?! Not in DB!")
            self.detach_session_cart()
            return self.current_session_cart
        return skel  # type: ignore

    def _ensure_current_session_cart(self) -> db.Key:
        if not self.session.get("session_cart_key"):
            root_node = self.addSkel("node")
            root_node["is_root_node"] = True
            root_node["name"] = root_node.name.getDefaultValue(root_node)
            root_node["cart_type"] = CartType.BASKET
            root_node.write()
            self.session["session_cart_key"] = root_node["key"]
            current.session.get().markChanged()
            # Store basket at the user skel, it will be shared over multiple sessions / devices
            if user := current.user.get():
                self._set_basket_txn(user_key=user["key"], basket_key=root_node["key"])
        return self.session["session_cart_key"]

    def detach_session_cart(self) -> db.Key | None:
        """
        Unlink the current cart from the session (and the user's basket).

        The cart entity itself is kept.  Tolerates a session that has no
        ``session_cart_key`` (anymore) instead of raising a ``KeyError``.

        :return: The key of the detached cart, or ``None`` if none was set.
        """
        key = self.session.get("session_cart_key")
        self.session["session_cart_key"] = None
        current.session.get().markChanged()
        if user := current.user.get():
            self._set_basket_txn(user_key=user["key"], basket_key=None)
        return key

    @staticmethod
    def _set_basket_txn(user_key: db.Key, basket_key: db.Key | None) -> SkeletonInstance:
        if not db.IsInTransaction():
            return db.RunInTransaction(Cart._set_basket_txn, user_key=user_key, basket_key=basket_key)
        user_skel = conf.main_app.vi.user.editSkel()
        user_skel.read(user_key)
        user_skel.setBoneValue("basket", basket_key)
        user_skel.write()
        return user_skel

    def get_available_root_nodes(self, *args, **kwargs) -> list[dict[t.Literal["name", "key"], str]]:
        root_nodes = []
        if self.current_session_cart_key is not None:
            root_nodes.append(self.current_session_cart)

        if user := current.user.get():
            for wishlist in user["wishlist"]:
                root_nodes.append({
                    "key": wishlist["key"],
                    "name": wishlist["name"],
                    "cart_type": CartType.WISHLIST,
                })

        return root_nodes

    # deprecated! viur-core support
    getAvailableRootNodes = get_available_root_nodes

    @exposed
    def listRootNodes(self, *args, **kwargs) -> t.Any:
        """
        Renders a list of all available repositories for the current user using the
        modules default renderer.

        :returns: The rendered representation of the available root-nodes.
        """
        return self.render.listRootNodes([
            self.render.renderSkelValues(skel)
            for skel in self.getAvailableRootNodes(*args, **kwargs)
        ])

    # --- helpers -------------------------------------------------------------

    def is_valid_node(
        self,
        node_key: db.Key,
        root_node: bool = False,
    ) -> bool:
        """
        is this a valid node key for the user?

        :param node_key: Key of node to check
        :param root_node: Must this be a root node, or is any node okay?
        """
        # TODO: return (okay_status, reason, skel) tuple/Dataclass?
        skel = self.viewSkel("node")
        if not skel.read(node_key):
            logger.debug(f"fail reason: 404")
            return False
        # logger.debug(f'{skel=}')
        if root_node and not skel["is_root_node"]:
            # The node is not a root node, but a root node is expected
            logger.debug(f"fail reason: not a root node")
            return False
        available_root_nodes = self.get_available_root_nodes()
        available_root_nodes_keys = [rn["key"] for rn in available_root_nodes]
        if skel["is_root_node"] and skel["key"] not in available_root_nodes_keys:
            # The node is a root node, but not from the user
            logger.debug(f"fail reason: not a valid root node key")
            return False
        if not skel["is_root_node"] and skel["parentrepo"] not in available_root_nodes_keys:
            # The node is a node, but the root node is not from the user
            logger.debug(f"fail reason: not a child of valid root node")
            logger.debug(f'{skel["parentrepo"]=} // {available_root_nodes_keys=}')
            return False
        return True

    def get_children(
        self,
        parent_cart_key: db.Key,
        **filters: t.Any,
    ) -> t.Iterator[SkeletonInstance]:
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key. Got {parent_cart_key!r} instead")
        for skel_type in ("node", "leaf"):
            skel = self.viewSkel(skel_type)
            query = skel.all().mergeExternalFilter(filters)
            query = query.order(("sortindex", db.SortOrder.Ascending))
            # TODO: query = self.listFilter(query)
            if query is None:
                raise errors.Unauthorized()
            query.filter("parententry =", parent_cart_key)
            yield from query.fetch(MAX_FETCH_LIMIT)

    def get_children_from_cache(
        self,
        parent_cart_key: db.Key
    ) -> list[SkeletonInstance]:
        cache = current.request_data.get().setdefault("shop_cache_cart_children", {})
        try:
            return [without_render_preparation(s) for s in cache[parent_cart_key]]
        except KeyError:
            pass
        children = list(self.get_children(parent_cart_key))
        cache[parent_cart_key] = children
        return children

    def clear_children_cache(self) -> None:
        current.request_data.get()["shop_cache_cart_children"] = {}

    # --- (internal) API methods ----------------------------------------------

    def cart_get(
        self,
        cart_key: db.Key,
        skel_type: SkelType,
    ) -> SkeletonInstance_T[CartNodeSkel | CartItemSkel] | None:
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")
        skel = self.viewSkel(skel_type)
        if not skel.read(cart_key):
            logger.debug(f"Cart {cart_key} does not exist")
            return None
        if not self.canView(skel_type, skel):
            logger.debug(f"Cart {cart_key} is forbidden by canView")
            return None
        return skel

    def get_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        *,
        must_be_listed: bool = True,
    ) -> SkeletonInstance_T[CartItemSkel]:
        if not isinstance(article_key, db.Key):
            raise TypeError(f"article_key must be an instance of db.Key")
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not self.is_valid_node(parent_cart_key):
            raise e.InvalidArgumentException("parent_cart_key", parent_cart_key)
        skel = self.viewSkel("leaf")
        query: db.Query = skel.all()
        query.filter("parententry =", parent_cart_key)
        query.filter("article.dest.__key__ =", article_key)
        if must_be_listed:
            query.filter("shop_listed =", True)
        skel = query.getSkel()
        return skel  # type: ignore

    def add_or_update_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        *,
        quantity: int,
        quantity_mode: QuantityMode,
        **kwargs,
    ) -> SkeletonInstance_T[CartItemSkel] | None:
        if not isinstance(article_key, db.Key):
            raise TypeError(f"article_key must be an instance of db.Key")
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not isinstance(quantity_mode, QuantityMode):
            raise TypeError(f"quantity_mode must be an instance of QuantityMode")
        if not self.is_valid_node(parent_cart_key):
            raise e.InvalidArgumentException("parent_cart_key", parent_cart_key)
        parent_skel = None
        if not (skel := self.get_article(article_key, parent_cart_key, must_be_listed=False)):
            # FIXME: This part between get_article() and skel.write() is open for race conditions
            #        parallel request might result into two different cart leafs with the same article.
            logger.info("This is an add")
            skel: SkeletonInstance_T[CartItemSkel] = self.addSkel("leaf")  # type:ignore
            res = skel.setBoneValue("article", article_key)
            skel["parententry"] = parent_cart_key
            parent_skel = self.viewSkel("node")
            assert parent_skel.read(parent_cart_key)
            if parent_skel["is_root_node"]:
                skel["parentrepo"] = parent_skel["key"]
            else:
                skel["parentrepo"] = parent_skel["parentrepo"]
            article_skel: SkeletonInstance_T[ArticleAbstractSkel] = self.shop.article_skel()  # type: ignore
            if not article_skel.read(article_key):
                raise errors.NotFound(f"Article with key {article_key=} does not exist!")
            if not article_skel["shop_listed"]:
                # logger.debug(f"not listed: {article_skel=}")
                raise errors.UnprocessableEntity(f"Article is not listed for the shop!")
            skel = self.copy_article_values(article_skel, skel)
        else:
            parent_skel = skel.parent_skel
        if parent_skel and parent_skel["is_frozen"]:
            # The cart belongs to a placed order and must not change anymore
            raise errors.Forbidden(
                translate("viur.shop.error.cart.is_frozen",
                          default_variables={"cart_key": parent_skel["key"]})
            )
        if quantity == 0 and quantity_mode in (QuantityMode.INCREASE, QuantityMode.DECREASE):
            raise e.InvalidArgumentException(
                "quantity",
                descr_appendix="Increase/Decrease quantity by zero is pointless",
            )
        if quantity_mode == QuantityMode.REPLACE:
            skel["quantity"] = quantity
        elif quantity_mode == QuantityMode.DECREASE:
            skel["quantity"] -= quantity
        elif quantity_mode == QuantityMode.INCREASE:
            skel["quantity"] += quantity
        else:
            raise e.InvalidArgumentException("quantity_mode", quantity_mode)
        if skel["quantity"] < 0:
            raise e.InvalidArgumentException(
                "quantity",
                descr_appendix=f'Quantity cannot be negative! (reached {skel["quantity"]})'
            )
        if skel["quantity"] == 0:
            skel.delete()
            EVENT_SERVICE.call(Event.ARTICLE_CHANGED, skel=skel, deleted=True)
            return None
        try:
            discount_type = parent_skel["discount"]["dest"]["discount_type"]
        except (TypeError, KeyError) as exc:
            discount_type = None
        logger.debug(f"{discount_type=}")
        if discount_type == DiscountType.FREE_ARTICLE and skel["quantity"] > 1:
            raise e.InvalidArgumentException(
                "quantity",
                descr_appendix=f'Quantity of free article cannot be greater than 1! (reached {skel["quantity"]})'
            )
        skel = self.additional_add_or_update_article(skel, **kwargs)
        skel.write()
        EVENT_SERVICE.call(Event.ARTICLE_CHANGED, skel=skel, deleted=False)
        self.clear_children_cache()
        # TODO: Validate quantity with hook (stock availability)
        return skel

    def copy_article_values(
        self,
        article_skel: SkeletonInstance_T[ArticleAbstractSkel],
        skel: SkeletonInstance_T[CartItemSkel],
    ) -> SkeletonInstance_T[CartItemSkel]:
        """Copy values from the article to the cart leaf"""
        for bone in skel.keys():
            if not bone.startswith("shop_"):
                continue
            instance = getattr(article_skel.skeletonCls, bone)
            if isinstance(instance, BaseBone):
                value = article_skel[bone]
            elif isinstance(instance, property):
                value = getattr(article_skel, bone)
            else:
                raise NotImplementedError
            skel[bone] = value
        return skel

    def move_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        new_parent_cart_key: db.Key,
    ) -> SkeletonInstance_T[CartItemSkel] | None:
        if not isinstance(article_key, db.Key):
            raise TypeError(f"article_key must be an instance of db.Key")
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not isinstance(new_parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not (skel := self.get_article(article_key, parent_cart_key, must_be_listed=False)):
            raise e.InvalidArgumentException(
                "article_key",
                descr_appendix=f"Article does not exist in cart node {parent_cart_key}."
            )
        parent_skel = self.viewSkel("node")
        if not self.is_valid_node(new_parent_cart_key):
            raise e.InvalidArgumentException("parent_cart_key", parent_cart_key)
        if not parent_skel.read(new_parent_cart_key):
            raise e.InvalidArgumentException(
                "new_parent_cart_key", new_parent_cart_key,
                f"Target cart node does not exist"
            )
        if parent_skel["parentrepo"] != skel["parentrepo"]:
            raise e.InvalidArgumentException(
                "new_parent_cart_key", new_parent_cart_key,
                f"Target cart node is inside a different repo"
            )
        if skel["is_frozen"] or parent_skel["is_frozen"]:
            # Neither an ordered (frozen) item may be moved away
            # nor may an item be moved into a frozen cart
            frozen_cart_key = parent_cart_key if skel["is_frozen"] else new_parent_cart_key
            raise errors.Forbidden(
                translate("viur.shop.error.cart.is_frozen",
                          default_variables={"cart_key": frozen_cart_key})
            )
        skel["parententry"] = new_parent_cart_key
        skel.write()
        EVENT_SERVICE.call(Event.ARTICLE_CHANGED, skel=skel, deleted=False)
        return skel

    def cart_add(
        self,
        *,
        parent_cart_key: str | db.Key = None,
        cart_type: CartType = None,
        name: str = SENTINEL,
        customer_comment: str = SENTINEL,
        shipping_address_key: str | db.Key = SENTINEL,
        shipping_key: str | db.Key = SENTINEL,
        discount_key: str | db.Key = SENTINEL,
        **kwargs,
    ) -> SkeletonInstance_T[CartNodeSkel] | None:
        if not isinstance(parent_cart_key, (db.Key, type(None))):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not isinstance(cart_type, (CartType, type(None))):
            raise TypeError(f"cart_type must be an instance of CartType")
        if discount_key is not SENTINEL and not isinstance(discount_key, (db.Key, type(None))):
            raise TypeError(f"discount_key must be an instance of db.Key")
        skel = self.addSkel("node")
        skel = self._cart_set_values(
            skel=skel,
            cart_type=cart_type,
            parent_cart_key=parent_cart_key,
            name=name,
            customer_comment=customer_comment,
            shipping_address_key=shipping_address_key,
            shipping_key=shipping_key,
            discount_key=discount_key,
        )
        skel = self.additional_cart_add(skel, **kwargs)
        skel.write()
        EVENT_SERVICE.call(Event.CART_CHANGED, skel=skel, deleted=False)
        self.onAdded("node", skel)
        return skel

    def cart_update(
        self,
        cart_key: db.Key,
        *,
        parent_cart_key: str | db.Key = SENTINEL,
        cart_type: CartType = None,
        name: str = SENTINEL,
        customer_comment: str = SENTINEL,
        shipping_address_key: str | db.Key = SENTINEL,
        shipping_key: str | db.Key = SENTINEL,
        discount_key: str | db.Key = SENTINEL,
        **kwargs,
    ) -> SkeletonInstance_T[CartNodeSkel] | None:
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")
        if cart_type is not SENTINEL and not isinstance(cart_type, (CartType, type(None))):
            raise TypeError(f"cart_type must be an instance of CartType")
        if parent_cart_key is not SENTINEL and not isinstance(parent_cart_key, (db.Key, type(None))):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if discount_key is not SENTINEL and not isinstance(discount_key, (db.Key, type(None))):
            raise TypeError(f"discount_key must be an instance of db.Key")
        skel = self.editSkel("node")
        # TODO: must be inside a own root node ...
        # if not self.canEdit(skel):
        #     raise errors.Forbidden
        assert skel.read(cart_key)
        if skel["is_frozen"]:
            # The cart belongs to a placed order and must not change anymore
            raise errors.Forbidden(
                translate("viur.shop.error.cart.is_frozen",
                          default_variables={"cart_key": cart_key})
            )
        skel = self._cart_set_values(
            skel=skel,
            parent_cart_key=parent_cart_key,
            name=name,
            customer_comment=customer_comment,
            shipping_address_key=shipping_address_key,
            shipping_key=shipping_key,
            discount_key=discount_key,
        )
        self.additional_cart_update(skel, **kwargs)
        skel.write()
        EVENT_SERVICE.call(Event.CART_CHANGED, skel=skel, deleted=False)
        return skel

    def _cart_set_values(
        self,
        skel: SkeletonInstance | CartNodeSkel,
        *,
        parent_cart_key: db.Key = SENTINEL,
        cart_type: CartType = None,  # TODO: since we generate basket automatically,
        #                                    wishlist would be the only acceptable value ...
        name: str = SENTINEL,
        customer_comment: str = SENTINEL,
        shipping_address_key: str | db.Key = SENTINEL,
        shipping_key: str | db.Key = SENTINEL,
        discount_key: str | db.Key = SENTINEL,
    ) -> SkeletonInstance_T[CartNodeSkel]:
        if parent_cart_key is not SENTINEL:
            skel["parententry"] = parent_cart_key
            if parent_cart_key is None:
                skel["is_root_node"] = True
            else:
                skel["is_root_node"] = False
                if not self.is_valid_node(parent_cart_key):
                    raise e.InvalidArgumentException("parent_cart_key", parent_cart_key)
                parent_skel = self.viewSkel("node")
                assert parent_skel.read(parent_cart_key)
                if parent_skel["is_root_node"]:
                    skel["parentrepo"] = parent_skel["key"]
                else:
                    skel["parentrepo"] = parent_skel["parentrepo"]
        # Set / Change only values which were explicitly provided
        if name is not SENTINEL:
            skel["name"] = name
        if customer_comment is not SENTINEL:
            skel["customer_comment"] = customer_comment
        if shipping_address_key is not SENTINEL:
            if shipping_address_key is None:
                skel["shipping_address"] = None
            else:
                skel.setBoneValue("shipping_address", shipping_address_key)
                if AddressType.SHIPPING.value not in (
                    addr.value for addr in skel["shipping_address"]["dest"]["address_type"]
                ):
                    raise e.InvalidArgumentException(
                        "shipping_address",
                        descr_appendix="Address is not of type shipping."
                    )
        if shipping_key is not SENTINEL:
            if shipping_key is None:
                skel["shipping"] = None
                skel["shipping_status"] = ShippingStatus.CHEAPEST
            else:
                skel["shipping_status"] = ShippingStatus.USER
                # FIXME: Ensure it's a valid shipping for the cart
                skel.setBoneValue("shipping", shipping_key)

        if discount_key is not SENTINEL:
            if discount_key is None:
                skel["discount"] = None
            else:
                skel.setBoneValue("discount", discount_key)
        return skel

    def cart_remove(
        self,
        cart_key: db.Key,
    ) -> None:
        """
        Remove a cart node with its entire subtree.

        The subtree is deleted bottom-up and **before** the node itself:
        leafs first, then sub-nodes, the given node last.  This order keeps
        the tree consistent at any point in time -- if the process crashes
        in between, no children can be left behind whose ``parententry``
        points to an already deleted node (orphaned entries).  A repeated
        call simply continues the work (idempotent).

        Frozen carts belong to an order and cannot be removed.

        This also checks upfront whether the node is locked by a
        ``RelationalConsistency.PreventDeletion`` relation (e.g. an order
        referencing an in-progress checkout cart that has not been frozen
        yet) and fails before touching any child -- deleting the children
        first and finding out only at ``skel.delete()`` that the node itself
        is locked would leave the order pointing at an emptied-out cart.

        :param cart_key: Key of the cart node to remove.
        :raises errors.NotFound: If the cart node does not exist.
        :raises errors.Forbidden: If the cart node is frozen.
        :raises errors.Locked: If the cart node is referenced by a
            PreventDeletion relation (e.g. an order).
        """
        skel = self.editSkel("node")
        if not skel.read(cart_key):
            raise errors.NotFound
        if skel["is_frozen"]:
            raise errors.Forbidden(
                translate("viur.shop.error.cart.is_frozen",
                          default_variables={"cart_key": cart_key})
            )
        if (
            db.Query("viur-relations")
                .filter("dest.__key__ =", cart_key)
                .filter("viur_relational_consistency =", RelationalConsistency.PreventDeletion.value)
                .getEntry()
        ) is not None:
            raise errors.Locked("This entry is still referenced by other Skeletons, which prevents deleting!")
        self._delete_children(cart_key)
        skel.delete()
        if skel["parententry"] is None or skel["is_root_node"]:
            logger.info(f"{skel['key']} was a root node!")
            # raise NotImplementedError("Cannot delete root node")
            # TODO: remove relation or block deletion
            if skel["key"] == self.current_session_cart_key:
                self.detach_session_cart()
                # del self.session["session_cart_key"]
                # current.session.get().markChanged()
        EVENT_SERVICE.call(Event.CART_CHANGED, skel=skel, deleted=True)

    def _delete_children(self, parent_cart_key: db.Key) -> None:
        """
        Delete all children of a cart node bottom-up and synchronously.

        Leafs of *parent_cart_key* are deleted first, then each sub-node is
        processed recursively (its own children before the sub-node itself).

        Deliberately does not call the inherited :meth:`deleteRecursive` of
        the Tree prototype: that method is ``@CallDeferred`` and only deletes
        the children, while the node itself is deleted synchronously by the
        caller right away (see :meth:`Tree.delete` / :meth:`cart_remove`).
        If that deferred task gets lost (queue purge, crash, or the task
        being pinned to an App Engine version that no longer exists), the
        node is gone but its children survive it forever -- orphaned
        entries whose broken ``parententry`` chain crashes price
        computations and ``update_relations`` tasks later. Cart trees are
        small (a handful of nodes/leafs), so there is no need to defer this
        work at all; running it synchronously, bottom-up and before the
        node itself is deleted removes the race entirely instead of just
        narrowing it.

        :param parent_cart_key: Key of the cart node whose subtree gets deleted.
        """
        for leaf_skel in toolkit.iter_skel(self.editSkel("leaf").all().filter("parententry =", parent_cart_key)):
            leaf_skel.delete()
        for node_skel in toolkit.iter_skel(self.editSkel("node").all().filter("parententry =", parent_cart_key)):
            self._delete_children(node_skel["key"])
            node_skel.delete()

    def cart_clear(
        self,
        cart_key: db.Key,
        *,
        keep_sub_carts: bool = False,
    ) -> None:
        cart_skel = self.editSkel("node")
        if not cart_skel.read(cart_key):
            raise errors.NotFound
        if cart_skel["is_frozen"]:
            raise errors.Forbidden(
                translate("viur.shop.error.cart.is_frozen",
                          default_variables={"cart_key": cart_key})
            )

        for leaf_skel in toolkit.iter_skel(self.editSkel("leaf").all().filter("parententry =", cart_skel["key"])):
            leaf_skel.delete()

        if not keep_sub_carts:
            for node_skel in toolkit.iter_skel(self.editSkel("node").all().filter("parententry =", cart_skel["key"])):
                self.cart_clear(node_skel["key"], keep_sub_carts=keep_sub_carts)
                node_skel.delete()

        EVENT_SERVICE.call(Event.CART_CHANGED, skel=cart_skel, cleared=True)

    # --- Hooks ---------------------------------------------------------------

    def additional_add_or_update_article(
        self,
        skel: SkeletonInstance_T[CartItemSkel],
        /,
        **kwargs,
    ) -> SkeletonInstance_T[CartItemSkel]:
        """
        Hook method called by :meth:`add_or_update_article` before the skeleton is saved.

        This method can be overridden in a subclass to implement additional API fields or
        make further modifications to the cart skeleton (`skel`).
        By default, it raises an exception if unexpected arguments
        (``kwargs``) are provided and returns the unchanged `skel` object.

        :param skel: The current instance of the cart item skeleton.
        :param kwargs: Additional optional arguments for extended implementations.
        :raises TooManyArgumentsException: If unexpected arguments are passed in ``kwargs``.
        :return: The (potentially modified) cart item skeleton.
        """
        if kwargs:
            raise e.TooManyArgumentsException(f"{self}.add_or_update_article", *kwargs.keys())
        return skel

    def additional_cart_add(
        self,
        skel: SkeletonInstance_T[CartNodeSkel],
        /,
        **kwargs,
    ) -> SkeletonInstance_T[CartNodeSkel]:
        """
        Hook method called by :meth:`cart_add` before the skeleton is saved.

        This method can be overridden in a subclass to implement additional API fields or
        make further modifications to the cart skeleton (`skel`).
        By default, it raises an exception if unexpected arguments
        (``kwargs``) are provided and returns the unchanged `skel` object.

        :param skel: The current instance of the cart skeleton.
        :param kwargs: Additional optional arguments for extended implementations.
        :raises TooManyArgumentsException: If unexpected arguments are passed in ``kwargs``.
        :return: The (potentially modified) cart skeleton.
        """
        if kwargs:
            raise e.TooManyArgumentsException(f"{self}.cart_add", *kwargs.keys())
        return skel

    def additional_cart_update(
        self,
        skel: SkeletonInstance_T[CartNodeSkel],
        /,
        **kwargs,
    ) -> SkeletonInstance_T[CartNodeSkel]:
        """
        Hook method called by :meth:`cart_update` before the skeleton is saved.

        This method can be overridden in a subclass to implement additional API fields or
        make further modifications to the cart skeleton (`skel`).
        By default, it raises an exception if unexpected arguments
        (``kwargs``) are provided and returns the unchanged `skel` object.

        :param skel: The current instance of the cart skeleton.
        :param kwargs: Additional optional arguments for extended implementations.
        :raises TooManyArgumentsException: If unexpected arguments are passed in ``kwargs``.
        :return: The (potentially modified) cart skeleton.
        """
        if kwargs:
            raise e.TooManyArgumentsException(f"{self}.cart_update", *kwargs.keys())
        return skel

    # --- Cart / order calculations -------------------------------------------

    def freeze_cart(
        self,
        cart_key: db.Key,
    ) -> SkeletonInstance_T[CartNodeSkel]:
        """Freeze (lock) cart values and children items.

        :param cart_key: Key of the (sub-)cart skeleton.
        :return: The frozen CartNode skeleton.
        """
        # Iterate the children without a fetch limit: a partially frozen
        # cart would keep recomputing (and thereby changing) the totals of
        # the unfrozen entries after the order has been placed.
        child: SkeletonInstance_T[CartNodeSkel | CartItemSkel]
        for skel_type in ("node", "leaf"):
            for child in toolkit.iter_skel(
                self.viewSkel(skel_type).all().filter("parententry =", cart_key)
            ):
                if skel_type == "node":
                    self.freeze_cart(child["key"])
                else:
                    self.freeze_leaf(child)

        self.clear_children_cache()

        cart_skel = self.editSkel("node")
        assert cart_skel.read(cart_key)

        # Clone the address, so in case the user edits the address, existing orders wouldn't be affected by this
        try:
            sa_key = cart_skel["shipping_address"]["dest"]["key"]
        except (TypeError, KeyError):  # sub-carts might have no own shipping
            sa_key = None
        if sa_key is not None:
            sa_skel = self.shop.address.clone_address(sa_key)
            assert sa_skel["key"] != sa_key, f'{sa_skel["key"]} != {sa_key}'
            cart_skel.setBoneValue("shipping_address", sa_skel["key"])

        cart_skel["frozen_values"] = {
            "total": cart_skel["total"],
            "total_raw": cart_skel["total_raw"],
            "total_discount_price": cart_skel["total_discount_price"],
            "vat": cart_skel["vat"],
            "total_quantity": cart_skel["total_quantity"],
            "shipping": cart_skel["shipping"],
            "discount": make_json_dumpable(cart_skel["discount"]),
        }
        cart_skel["is_frozen"] = True
        cart_skel.write()
        return cart_skel  # type: ignore

    def freeze_leaf(self, leaf_skel: SkeletonInstance_T[CartItemSkel]):
        leaf_skel = self.copy_article_values(leaf_skel.article_skel_full, leaf_skel)
        leaf_skel["frozen_values"] = {
            "price": leaf_skel["price"],
            "shipping": leaf_skel["shipping"],
        }
        leaf_skel["is_frozen"] = True
        leaf_skel.write()
        return leaf_skel

    # -------------------------------------------------------------------------

    def get_discount_for_leaf(
        self,
        leaf_key_or_skel: db.Key | SkeletonInstance,
    ) -> list[SkeletonInstance]:
        """
        Collect the discounts of all cart nodes above the given leaf.

        Walks the ``parententry`` chain from the leaf up to the root node and
        collects the ``discount`` relation of every node on the way.

        The walk is tolerant against broken tree data: if a parent node does
        not exist anymore (orphaned entry) or the chain contains a cycle, the
        walk stops at the broken link with a warning and the discounts
        collected so far are returned.  This keeps computed bones (e.g. the
        price) usable on orphaned entries instead of raising and thereby
        crashing deferred tasks (like ``update_relations``) forever.

        :param leaf_key_or_skel: Key or skeleton of the cart leaf to start from.
        :return: The discount ref-skels found on the ancestor nodes.
        """
        if isinstance(leaf_key_or_skel, db.Key):
            skel = self.viewSkel("leaf")
            skel.read(leaf_key_or_skel)
        else:
            skel = leaf_key_or_skel
        discounts = []
        seen_keys = set()
        while (pk := skel["parententry"]):
            if pk in seen_keys:
                logger.warning(f"Cyclic parententry chain detected at {pk=}; stopping walk")
                break
            seen_keys.add(pk)
            skel = self.viewSkel("node", sub_skel="discount")
            if not skel.read(pk):
                logger.warning(f"Parent node {pk=} doesn't exist (anymore); stopping walk at orphaned entry")
                break
            if discount := skel["discount"]:
                discounts.append(discount["dest"])
        return discounts

    def add_new_parent(self, leaf_skel, **kwargs):
        new_parent_skel = self.addSkel("node")
        new_parent_skel["parententry"] = leaf_skel["parententry"]
        new_parent_skel["parentrepo"] = leaf_skel["parentrepo"]
        for key, value in kwargs.items():
            new_parent_skel[key] = value  # TODO: use .setBoneValue?
        self.onAdd("node", new_parent_skel)
        new_parent_skel.write()
        self.onAdded("node", new_parent_skel)
        EVENT_SERVICE.call(Event.CART_CHANGED, skel=new_parent_skel, deleted=False)
        leaf_skel["parententry"] = new_parent_skel["key"]
        leaf_skel.write()
        EVENT_SERVICE.call(Event.ARTICLE_CHANGED, skel=leaf_skel, deleted=False)
        return new_parent_skel

    def get_cached_cart_skel(self, key: db.Key) -> SkeletonInstance_T[CartNodeSkel] | None:
        """
        Read a cart node skeleton with request-local caching.

        :param key: Key of the cart node to read.
        :return: The cached or freshly read node skeleton or ``None`` if the
            node does not exist (anymore).  Missing nodes are not cached, so a
            later call re-checks the datastore.
        """
        cache = current.request_data.get().setdefault("shop_cache_cart_skel", {})
        key = db.keyHelper(key, CartNodeSkel.kindName)
        try:
            parent_skel = cache[key]
        except KeyError:
            parent_skel = self.viewSkel("node")
            if not parent_skel.read(key):
                logger.warning(f"Cart node {key=} doesn't exist (anymore)")
                return None
            cache[key] = parent_skel
        return parent_skel

    def get_closest_node(
        self,
        start: SkeletonInstance_T[CartNodeSkel | CartItemSkel],
        condition: t.Callable[[SkeletonInstance], bool] = (lambda skel: True),
    ) -> SkeletonInstance_T[CartNodeSkel] | None:
        """
        Walk the ``parententry`` chain upwards and return the first ancestor
        node that satisfies *condition*.

        The walk stops and returns ``None`` when

        *   the root node is reached without a match,
        *   the current entry has no ``parententry`` (detached entry),
        *   a parent node does not exist anymore (orphaned entry) or
        *   the ``parententry`` chain contains a cycle.

        The latter cases are broken tree states which must not crash callers
        like the price computation running inside deferred tasks.

        :param start: Leaf or node skeleton to start from (itself excluded).
        :param condition: Predicate evaluated for each ancestor node.
        :return: The closest matching ancestor node or ``None``.
        """
        seen_keys = set()
        while True:
            if not (pk := start["parententry"]) or pk in seen_keys:
                return None  # detached entry or cyclic parententry chain
            seen_keys.add(pk)
            if (parent_skel := self.get_cached_cart_skel(pk)) is None:
                return None  # orphaned entry, the parent node has been deleted
            if condition(parent_skel):
                return parent_skel  # type:ignore
            if parent_skel["is_root_node"]:
                return None  # NotFound
            start = parent_skel


try:
    Session.on_delete
except AttributeError:  # backward compatibility for viur-core
    from viur.core.version import __version__

    logger.warning(f"viur-core {__version__} has no Session.on_delete")
    Session.on_delete = lambda *_, **__: None


@Session.on_delete
def delete_guest_cart(session: db.Entity) -> None:
    """
    Delete carts from guest sessions to avoid orphaned carts.

    Runs as :meth:`Session.on_delete` hook.  Any failure is logged and
    swallowed: this hook must never prevent the session deletion itself.
    Carts that are referenced by an order, already gone or frozen are
    left alone.
    """
    if session["user"] != Session.GUEST_USER:
        return
    try:
        cart = session["data"]["shop"]["cart"]["session_cart_key"]
    except (KeyError, TypeError):
        return
    try:
        if (
            SHOP_INSTANCE.get().order.skel().all()
                .filter("cart.dest.__key__", cart)
                .getSkel()
        ) is not None:
            # Is used by an order
            return
        SHOP_INSTANCE.get().cart.cart_remove(cart)
        logger.debug(f"Deleted {cart=} and children after deleting {session=}")
    except errors.NotFound:
        logger.info(f"Cart {cart!r} of deleted session doesn't exist (anymore); nothing to do")
    except errors.Forbidden:
        logger.info(f"Cart {cart!r} of deleted session is frozen; keeping it")
    except Exception:
        logger.exception(f"Failed to delete guest cart {cart!r}; keeping it")
