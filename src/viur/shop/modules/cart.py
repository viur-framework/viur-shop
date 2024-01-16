import logging
import typing as t

from viur.core import conf, current, db, errors, utils
from viur.core.bones import BaseBone
from viur.core.prototypes import Tree
from viur.core.skeleton import SkeletonInstance
from viur.shop.modules.abstract import ShopModuleAbstract
from ..constants import CartType, QuantityMode
from ..exceptions import InvalidStateError
from ..skeletons.cart import CartItemSkel, CartNodeSkel

logger = logging.getLogger("viur.shop").getChild(__name__)


class Cart(ShopModuleAbstract, Tree):
    nodeSkelCls = CartNodeSkel
    leafSkelCls = CartItemSkel

    @property
    def current_session_cart_key(self):
        if user := current.user.get():
            user_skel = conf.main_app.user.viewSkel()
            user_skel.fromDB(user["key"])
            if user_skel["basket"]:
                self.session["session_cart_key"] = user_skel["basket"]["dest"]["key"]
        self._ensure_current_session_cart()
        return self.session.get("session_cart_key")

    @property
    def current_session_cart(self):  # TODO: Caching
        skel = self.viewSkel("node")
        if not skel.fromDB(self.current_session_cart_key):
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
                user_skel = conf.main_app.user.editSkel()
                user_skel.fromDB(user["key"])
                user_skel.setBoneValue("basket", key)
                user_skel.toDB()
        return self.session["session_cart_key"]

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
    ) -> t.Iterator[list[dict]]:
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        for skel_type in ("node", "leaf"):
            skel = self.viewSkel(skel_type)
            query = skel.all().mergeExternalFilter(kwargs)
            # query = self.listFilter(query)
            if query is None:
                raise errors.Unauthorized()
            query.filter("parententry =", parent_cart_key)
            yield from query.fetch(100)

    def get_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
    ):
        if not isinstance(article_key, db.Key):
            raise TypeError(f"article_key must be an instance of db.Key")
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not self.is_valid_node(parent_cart_key):
            raise ValueError(f"Invalid (root) node (for this user).")
        skel = self.viewSkel("leaf")
        query: db.Query = skel.all()
        query.filter("parententry =", parent_cart_key)
        query.filter("article.dest.__key__ =", article_key)
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
            raise ValueError(f"Invalid (root) node (for this user).")
        if not (skel := self.get_article(article_key, parent_cart_key)):
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
            assert article_skel.fromDB(article_key)
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
        if quantity == 0 and quantity_mode in (QuantityMode.INCREASE, QuantityMode.DECREASE):
            raise ValueError(f"Increase/Decrease quantity by zero is pointless")
        if quantity_mode == QuantityMode.REPLACE:
            skel["quantity"] = quantity
        elif quantity_mode == QuantityMode.DECREASE:
            skel["quantity"] -= quantity
        elif quantity_mode == QuantityMode.INCREASE:
            skel["quantity"] += quantity
        else:
            raise ValueError(
                f"Invalid {quantity_mode=}! "
            )
        if skel["quantity"] < 0:
            raise ValueError(f'Quantity cannot be negative! (reached {skel["quantity"]})')
        if skel["quantity"] == 0:
            skel.delete()
            return None
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
        if not (skel := self.get_article(article_key, parent_cart_key)):
            raise ValueError(f"Article with {article_key=} does not exist in {parent_cart_key=}.")
        parent_skel = self.viewSkel("node")
        if not self.is_valid_node(new_parent_cart_key):
            raise ValueError(f"Invalid (root) node (for this user).")
        if not parent_skel.fromDB(new_parent_cart_key):
            raise ValueError(f"Target node with {new_parent_cart_key=} does not exist")
        if parent_skel["parentrepo"] != skel["parentrepo"]:
            raise ValueError(f"Target node is inside a different repo")
        skel["parententry"] = new_parent_cart_key  # TODO: validate permission?
        skel.toDB()
        return skel

    def cart_add(
        self,
        parent_cart_key: str | db.Key = None,
        cart_type: CartType = None,  # TODO: since we generate basket automatically,
        #                                    wishlist would be the only acceptable value ...
        name: str = None,
        customer_comment: str = None,
        shipping_address_key: str | db.Key = None,
        shipping_key: str | db.Key = None,
    ) -> SkeletonInstance | None:
        if not isinstance(parent_cart_key, (db.Key, type(None))):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not isinstance(cart_type, (CartType, type(None))):
            raise TypeError(f"cart_type must be an instance of CartType")
        skel = self.addSkel("node")
        skel["parententry"] = parent_cart_key
        if parent_cart_key is None:
            skel["is_root_node"] = True
        else:
            if not self.is_valid_node(parent_cart_key):
                raise ValueError(f"Invalid (root) node (for this user).")
            parent_skel = self.viewSkel("node")
            assert parent_skel.fromDB(parent_cart_key)
            if parent_skel["is_root_node"]:
                skel["parentrepo"] = parent_skel["key"]
            else:
                skel["parentrepo"] = parent_skel["parentrepo"]
        logger.debug(f"{current.request.get().kwargs = }")
        logger.debug(f"{current.request.get().args = }")
        # Set / Change only values which were explicitly provided
        if "name" in current.request.get().kwargs:
            skel["name"] = name
        if "customer_comment" in current.request.get().kwargs:
            skel["customer_comment"] = customer_comment
        if "shipping_address_key" in current.request.get().kwargs:
            skel.setBoneValue("shipping_address_key", shipping_address_key)
        if "shipping_key" in current.request.get().kwargs:
            skel.setBoneValue("shipping_key", shipping_key)
        skel.toDB()
        return skel

    def cart_remove(
        self,
        cart_key: db.Key,
    ) -> None:
        self.deleteRecursive(cart_key)
        skel = self.editSkel("node")
        skel.fromDB(cart_key)
        if skel["parententry"] is None or skel["is_root_node"]:
            logger.info(f"{skel['key']} was a root node!")
            raise NotImplementedError("Cannot delete root node")
            # TODO: remove relation or block deletion
            if skel["parententry"] == self.current_session_cart_key:
                del self.session["session_cart_key"]
                current.session.get().markChanged()
        skel.delete()
