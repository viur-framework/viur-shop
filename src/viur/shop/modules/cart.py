import typing as t  # noqa

import viur.shop.types.exceptions as e
from viur.core import conf, current, db, errors, exposed, utils
from viur.core.bones import BaseBone
from viur.core.prototypes import Tree
from viur.core.skeleton import SkeletonInstance
from viur.shop.modules.abstract import ShopModuleAbstract
from viur.shop.types import *
from viur.shop.types.exceptions import InvalidStateError
from ..globals import SENTINEL, SHOP_LOGGER
from ..skeletons.cart import CartItemSkel, CartNodeSkel

logger = SHOP_LOGGER.getChild(__name__)


class Cart(ShopModuleAbstract, Tree):
    nodeSkelCls = CartNodeSkel
    leafSkelCls = CartItemSkel

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "cart3"
        return admin_info

    # --- Session -------------------------------------------------------------

    @property
    def current_session_cart_key(self):
        if user := current.user.get():
            user_skel = conf.main_app.vi.user.viewSkel()
            user_skel.fromDB(user["key"])
            if user_skel["basket"]:
                self.session["session_cart_key"] = user_skel["basket"]["dest"]["key"]
        self._ensure_current_session_cart()
        return self.session.get("session_cart_key")

    @property
    def current_session_cart(self):  # TODO: Caching
        skel = self.viewSkel("node")
        if not skel.fromDB(self.current_session_cart_key):
            logger.critical(f"Invalid session_cart_key {self.current_session_cart_key} ?! Not in DB!")
            self.detach_session_cart()
            return self.current_session_cart
            raise InvalidStateError(f"Invalid session_cart_key {self.current_session_cart_key} ?! Not in DB!")
        return skel

    def _ensure_current_session_cart(self):
        if not self.session.get("session_cart_key"):
            root_node = self.addSkel("node")
            user = current.user.get() and current.user.get()["name"] or "__guest__"
            root_node["is_root_node"] = True
            root_node["name"] = f"Session Cart of {user} created at {utils.utcNow()}"
            root_node["cart_type"] = CartType.BASKET
            key = root_node.toDB()
            self.session["session_cart_key"] = key
            current.session.get().markChanged()
            # Store basket at the user skel, it will be shared over multiple sessions / devices
            if user := current.user.get():
                db.RunInTransaction(self._set_basket_txn, user_key=user["key"], basket_key=key)
        return self.session["session_cart_key"]

    def detach_session_cart(self) -> db.Key:
        key = self.session["session_cart_key"]
        self.session["session_cart_key"] = None
        current.session.get().markChanged()
        if user := current.user.get():
            db.RunInTransaction(self._set_basket_txn, user_key=user["key"], basket_key=None)
        return key

    @staticmethod
    def _set_basket_txn(user_key: db.Key, basket_key: db.Key | None) -> SkeletonInstance:
        user_skel = conf.main_app.vi.user.editSkel()
        user_skel.fromDB(user_key)
        user_skel.setBoneValue("basket", basket_key)
        user_skel.toDB()
        return user_skel

    def get_available_root_nodes(self, *args, **kwargs) -> list[dict[t.Literal["name", "key"], str]]:
        root_nodes = [self.current_session_cart]

        if user := current.user.get():
            for wishlist in user["wishlist"]:
                logger.debug(f"{wishlist = }")
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
        if utils.string.is_prefix(self.render.kind, "json"):
            # TODO: add in viur-core
            current.request.get().response.headers["Content-Type"] = "application/json"
        return self.render.listRootNodes([
            self.render.renderSkelValues(skel)
            for skel in self.getAvailableRootNodes(*args, **kwargs)
        ])

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
        if not skel.fromDB(node_key):
            logger.debug(f"fail reason: 404")
            return False
        logger.debug(f'{skel=}')
        if root_node and not skel["is_root_node"]:
            # The node is not a root node, but a root nodes is expected
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
        **kwargs
    ) -> t.Iterator[SkeletonInstance]:
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        for skel_type in ("node", "leaf"):
            skel = self.viewSkel(skel_type)
            query = skel.all().mergeExternalFilter(kwargs)
            query = query.order(("sortindex", db.SortOrder.Ascending))
            # TODO: query = self.listFilter(query)
            if query is None:
                raise errors.Unauthorized()
            query.filter("parententry =", parent_cart_key)
            yield from query.fetch(100)

    def get_children_from_cache(
        self,
        parent_cart_key: db.Key
    ) -> list[SkeletonInstance]:
        cache = current.request_data.get().setdefault("shop_cache_cart_children", {})
        try:
            return cache[parent_cart_key]
        except KeyError:
            pass
        children = list(self.get_children(parent_cart_key))
        cache[parent_cart_key] = children
        return children

    # --- (internal) API methods ----------------------------------------------

    def get_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        must_be_listed: bool = True,
    ):
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
        return skel

    def add_or_update_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        quantity: int,
        quantity_mode: QuantityMode,
    ) -> CartItemSkel | None:
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
            logger.info("This is an add")
            skel = self.addSkel("leaf")
            res = skel.setBoneValue("article", article_key)
            skel["parententry"] = parent_cart_key
            parent_skel = self.viewSkel("node")
            assert parent_skel.fromDB(parent_cart_key)
            if parent_skel["is_root_node"]:
                skel["parentrepo"] = parent_skel["key"]
            else:
                skel["parentrepo"] = parent_skel["parentrepo"]
            article_skel: SkeletonInstance = self.shop.article_skel()
            if not article_skel.fromDB(article_key):
                raise errors.NotFound(f"Article with key {article_key=} does not exist!")
            if not article_skel["shop_listed"]:
                raise errors.UnprocessableEntity(f"Article is not listed for the shop!")
            # Copy values from the article
            for bone in skel.keys():
                if not bone.startswith("shop_"): continue
                instance = getattr(article_skel.skeletonCls, bone)
                if isinstance(instance, BaseBone):
                    value = article_skel[bone]
                elif isinstance(instance, property):
                    value = getattr(article_skel, bone)
                else:
                    raise NotImplementedError
                skel[bone] = value
        else:
            parent_skel = skel.parent_skel
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
            return None
        try:
            discount_type = parent_skel["discount"]["dest"]["discount_type"]
        except (TypeError, KeyError) as exc:
            logger.debug(exc, exc_info=True)
            discount_type = None
        logger.debug(f"{discount_type=}")
        if discount_type == DiscountType.FREE_ARTICLE and skel["quantity"] > 1:
            raise e.InvalidArgumentException(
                "quantity",
                descr_appendix=f'Quantity of free article cannot be greater than 1! (reached {skel["quantity"]})'
            )
        # TODO: Validate quantity with hook (stock availability)
        key = skel.toDB()
        return skel

    def move_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        new_parent_cart_key: db.Key,
    ) -> CartItemSkel | None:
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
        if not parent_skel.fromDB(new_parent_cart_key):
            raise e.InvalidArgumentException(
                "new_parent_cart_key", new_parent_cart_key,
                f"Target cart node does not exist"
            )
        if parent_skel["parentrepo"] != skel["parentrepo"]:
            raise e.InvalidArgumentException(
                "new_parent_cart_key", new_parent_cart_key,
                f"Target cart node is inside a different repo"
            )
        skel["parententry"] = new_parent_cart_key
        skel.toDB()
        return skel

    def cart_add(
        self,
        parent_cart_key: str | db.Key = None,
        cart_type: CartType = None,  # TODO: since we generate basket automatically,
        #                                    wishlist would be the only acceptable value ...
        name: str = SENTINEL,
        customer_comment: str = SENTINEL,
        shipping_address_key: str | db.Key = SENTINEL,
        shipping_key: str | db.Key = SENTINEL,
        discount_key: str | db.Key = SENTINEL,
    ) -> SkeletonInstance | None:
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
        skel.toDB()
        return skel

    def cart_update(
        self,
        cart_key: db.Key,
        parent_cart_key: str | db.Key = SENTINEL,
        cart_type: CartType = None,  # TODO: since we generate basket automatically,
        #                                    wishlist would be the only acceptable value ...
        name: str = SENTINEL,
        customer_comment: str = SENTINEL,
        shipping_address_key: str | db.Key = SENTINEL,
        shipping_key: str | db.Key = SENTINEL,
        discount_key: str | db.Key = SENTINEL,
    ) -> SkeletonInstance | None:
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")
        if not isinstance(cart_type, (CartType, type(None))):
            raise TypeError(f"cart_type must be an instance of CartType")
        if parent_cart_key is not SENTINEL and not isinstance(parent_cart_key, (db.Key, type(None))):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if discount_key is not SENTINEL and not isinstance(discount_key, (db.Key, type(None))):
            raise TypeError(f"discount_key must be an instance of db.Key")
        skel = self.editSkel("node")
        # TODO: must be inside a own root node ...
        # if not self.canEdit(skel):
        #     raise errors.Forbidden
        assert skel.fromDB(cart_key)
        skel = self._cart_set_values(
            skel=skel,
            parent_cart_key=parent_cart_key,
            name=name,
            customer_comment=customer_comment,
            shipping_address_key=shipping_address_key,
            shipping_key=shipping_key,
            discount_key=discount_key,
        )
        skel.toDB()
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
    ) -> SkeletonInstance:
        if parent_cart_key is not SENTINEL:
            skel["parententry"] = parent_cart_key
            if parent_cart_key is None:
                skel["is_root_node"] = True
            else:
                skel["is_root_node"] = False
                if not self.is_valid_node(parent_cart_key):
                    raise e.InvalidArgumentException("parent_cart_key", parent_cart_key)
                parent_skel = self.viewSkel("node")
                assert parent_skel.fromDB(parent_cart_key)
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
                if skel["shipping_address"]["dest"]["address_type"] != AddressType.SHIPPING:
                    raise e.InvalidArgumentException(
                        "shipping_address",
                        descr_appendix="Address is not of type shipping."
                    )
        if shipping_key is not SENTINEL:
            if shipping_key is None:
                skel["shipping"] = None
            else:
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
        self.deleteRecursive(cart_key)
        skel = self.editSkel("node")
        if not skel.fromDB(cart_key):
            raise errors.NotFound
        if skel["parententry"] is None or skel["is_root_node"]:
            logger.info(f"{skel['key']} was a root node!")
            # raise NotImplementedError("Cannot delete root node")
            # TODO: remove relation or block deletion
            if skel["key"] == self.current_session_cart_key:
                self.detach_session_cart()
                # del self.session["session_cart_key"]
                # current.session.get().markChanged()
        skel.delete()

    # --- Cart / order calculations -------------------------------------------

    def freeze_cart(
        self,
        cart_key: db.Key,
    ) -> None:
        # TODO: for node in tree:
        #   freeze node with values, discount, shipping (JSON dump? bone duplication?)
        #   ensure each article still exists and shop_listed is True
        ...

    # -------------------------------------------------------------------------

    def get_discount_for_leaf(
        self,
        leaf_key_or_skel: db.Key | SkeletonInstance,
    ) -> list[SkeletonInstance]:
        if isinstance(leaf_key_or_skel, db.Key):
            skel = self.viewSkel("leaf")
            skel.fromDB(leaf_key_or_skel)
        else:
            skel = leaf_key_or_skel
        discounts = []
        while (pk := skel["parententry"]):
            skel = self.viewSkel("node")
            if not skel.fromDB(pk):
                raise InvalidStateError(f"{pk=} doesn't exist!")
            if discount := skel["discount"]:
                discounts.append(discount["dest"])
        logger.debug(f"{discounts = }")
        return discounts

    def add_new_parent(self, leaf_skel, **kwargs):
        new_parent_skel = self.addSkel("node")
        new_parent_skel["parententry"] = leaf_skel["parententry"]
        new_parent_skel["parentrepo"] = leaf_skel["parentrepo"]
        for key, value in kwargs.items():
            new_parent_skel[key] = value  # TODO: use .setBoneValue?
        new_parent_skel.toDB()
        leaf_skel["parententry"] = new_parent_skel["key"]
        leaf_skel.toDB()
        return new_parent_skel
