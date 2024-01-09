import logging
import typing as t

from viur.core import current, db, exposed, utils
from viur.core.prototypes import Tree
from viur.shop.modules.abstract import ShopModuleAbstract
from ..constants import CartType, QuantityModeType
from ..exceptions import InvalidStateError
from ..skeletons.cart import CartItemSkel, CartNodeSkel

logger = logging.getLogger("viur.shop").getChild(__name__)


class Cart(ShopModuleAbstract, Tree):
    nodeSkelCls = CartNodeSkel
    leafSkelCls = CartItemSkel

    @exposed
    def index(self):
        return "your cart is empty -.-"

    @property
    def current_session_cart_key(self):
        # TODO: Store in current_basket bone in the UserSkel of the user ?!
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
            root_node["name"] = f"Session Cart of {user} created at {utils.utcNow()}"
            key = root_node.toDB()
            self.session["session_cart_key"] = key
            current.session.get().markChanged()
        return self.session["session_cart_key"]

    def getAvailableRootNodes(self, *args, **kwargs) -> list[dict[t.Literal["name", "key"], str]]:
        root_nodes = [{
            "key": self.current_session_cart_key,
            "name": self.current_session_cart["name"],
            "cart_type": CartType.BASKET,
        }]

        if user := current.user.get():
            for wishlist in user["wishlist"]:
                logger.debug(f"{wishlist = }")
                root_nodes.append({
                    "key": wishlist["key"],
                    "name": wishlist["name"],
                    "cart_type": CartType.WISHLIST,
                })

        return root_nodes

    def get_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
    ):
        if not isinstance(article_key, db.Key):
            raise TypeError(f"article_key must be an instance of db.Key")
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        skel = self.viewSkel("leaf")
        query: db.Query = skel.all()
        query.filter("parententry =", parent_cart_key)
        query.filter("article.dest.__key__ =", article_key)
        skel = query.getSkel()
        logger.debug(f"{skel=}")
        return skel

    def add_or_update_article(
        self,
        article_key: db.Key,
        parent_cart_key: db.Key,
        quantity: int,
        quantity_mode: QuantityModeType,
    ) -> CartItemSkel:
        if not isinstance(article_key, db.Key):
            raise TypeError(f"article_key must be an instance of db.Key")
        if not isinstance(parent_cart_key, db.Key):
            raise TypeError(f"parent_cart_key must be an instance of db.Key")
        if not (skel := self.get_article(article_key, parent_cart_key)):
            skel = self.addSkel("leaf")
            res = skel.setBoneValue("article", article_key)
            logger.debug(f"article.setBoneValue : {res=}")
            skel["parententry"] = parent_cart_key
            parent_skel = self.viewSkel("node")
            parent_skel.fromDB(parent_cart_key)
            skel.setBoneValue("parentrepo", parent_skel["parentrepo"])
        if quantity_mode == "replace":
            skel["quantity"] = quantity
        elif quantity_mode == "decrease":
            skel["quantity"] -= quantity
        elif quantity_mode == "increase":
            skel["quantity"] += quantity
        else:
            raise ValueError(
                f"Invalid {quantity_mode=}! "
                f"Must be {' or '.join(vars(QuantityModeType)['__args__'])}."
            )
        key = skel.toDB()
        return skel
