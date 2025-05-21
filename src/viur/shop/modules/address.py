import typing as t

from viur.core import current, db, translate
from viur.core.prototypes import List
from viur.core.prototypes.skelmodule import DEFAULT_ORDER_TYPE
from viur.core.skeleton import SkeletonInstance
from .abstract import ShopModuleAbstract
from ..globals import SHOP_LOGGER
from ..skeletons import AddressSkel
from ..types import SkeletonInstance_T

logger = SHOP_LOGGER.getChild(__name__)


class Address(ShopModuleAbstract, List):
    moduleName = "address"
    kindName = "{{viur_shop_modulename}}_address"

    reference_user_created_skeletons_in_session = True

    default_order: DEFAULT_ORDER_TYPE = (
        ("firstname", db.SortOrder.Ascending),
        ("lastname", db.SortOrder.Ascending),
    )

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        admin_info["icon"] = "person-vcard"

        if user := current.user.get():
            admin_info.setdefault("views", []).append({
                "name": translate(
                    "viur.shop.my_addresses",
                    "My Addresses",
                ),
                "filter": {
                    "customer.dest.key": user["key"],
                    "cloned_from": "None",
                },
            })

        return admin_info

    def canAdd(self) -> bool:
        return True

    def canEdit(self, skel: SkeletonInstance) -> bool:
        if super().canEdit(skel):
            return True

        if skel["key"] in self.session.get("created_skel_keys", ()):
            logger.debug(f"User added this address in his session: {skel['key']!r}")
            return True

        return False

    def listFilter(self, query: db.Query) -> t.Optional[db.Query]:
        # The current customer is only allowed to see his own addresses
        if (user := current.user.get()) and self.render.kind == "json":
            query.filter("customer.dest.__key__ =", user["key"])
            query.filter("cloned_from =", None)

        if user and (f"{self.moduleName}-view" in user["access"] or "root" in user["access"]):
            return query

        return None

    def onAdded(self, skel: SkeletonInstance):
        super().onAdded(skel)
        self._disable_old_default(skel)

    def onEdited(self, skel: SkeletonInstance):
        super().onEdited(skel)
        self._disable_old_default(skel)

    def _disable_old_default(self, skel: SkeletonInstance) -> None:
        """Disable old is_default"""
        if not skel["is_default"] or not skel["address_type"] or not skel["customer"]:
            return
        query = self.editSkel().all() \
            .filter("is_default =", True) \
            .filter("customer.dest.__key__ =", skel["customer"]["dest"]["key"]) \
            .filter("address_type IN", [at.value for at in skel["address_type"]])
        for other_skel in query.fetch(100):
            if skel["key"] != other_skel["key"]:
                other_skel["is_default"] = False
                other_skel.write()

    def clone_address(self, key: db.Key) -> SkeletonInstance_T[AddressSkel]:
        # Clone the address, so in case the user edits the address, existing orders wouldn't be affected by this
        # TODO: Can we do this copy-on-write instead; clone if an address is edited and replace on used order skels?
        src_address_skel = address_skel = self.editSkel()
        if not address_skel.read(key):
            raise ValueError(f"Address with {key=!r} does not exist")
        # create a new instance and copy all values except the key
        address_skel = self.shop.address.addSkel()
        for name, value in src_address_skel.items(True):
            if name == "key":
                continue
            address_skel[name] = value
        address_skel.setBoneValue("cloned_from", key)
        address_skel.write()
        return address_skel


Address.json = True
