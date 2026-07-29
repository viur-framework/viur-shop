import typing as t

from viur.core.bones import RelationalBone, RelationalUpdateLevel
from viur.core.skeleton import SkeletonInstance

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class SnapshotRelationalBone(RelationalBone):
    """A :class:`RelationalBone` that keeps its cached ``refKeys`` copy in sync
    while the owning skeleton is still editable, and freezes that copy once the
    owning skeleton is frozen.

    Background
    ----------
    viur-core only offers a *static* :class:`RelationalUpdateLevel`, and neither
    value fits an order/cart address:

    - ``Always`` keeps the cached copy in sync with the referenced entity, but a
      completed (frozen) order would then change retroactively whenever the
      referenced address gets edited later.
    - ``OnValueAssignment`` freezes the copy at assignment time, but then never
      reflects edits made to the referenced entity during an ongoing checkout
      (e.g. the customer adds a birthdate in a later step or corrects the
      address) -- the stale copy is what gets persisted with the order.

    This bone combines both: it is configured with ``updateLevel=Always`` so the
    copy is kept in sync -- both by the ``update_relations`` task (triggered when
    the referenced entity changes) and by explicit :meth:`refresh` calls -- as
    long as the owning skeleton is *not* frozen, and turns :meth:`refresh` into a
    no-op once it *is* frozen, preserving the snapshot captured at freeze time.

    :param is_frozen: Callable deciding whether the owning skeleton is frozen and
        its snapshot must be preserved. Defaults to reading the boolean
        ``is_frozen`` bone.
    """

    def __init__(
        self,
        *args: t.Any,
        is_frozen: t.Callable[[SkeletonInstance], bool] = lambda skel: bool(skel["is_frozen"]),
        **kwargs: t.Any,
    ) -> None:
        # The live-sync behaviour relies on updateLevel=Always: it keeps the
        # relation in the update_relations query and prevents refresh() from
        # short-circuiting. Freezing is handled by refresh() below instead, so
        # any caller-provided updateLevel would break the contract and is
        # therefore overridden here.
        kwargs["updateLevel"] = RelationalUpdateLevel.Always
        super().__init__(*args, **kwargs)
        self.is_frozen = is_frozen

    def refresh(self, skel: SkeletonInstance, name: str) -> None:
        """Refresh the cached copy -- unless the owning skeleton is frozen, in
        which case the snapshot captured at freeze time is preserved."""
        if self.is_frozen(skel):
            logger.debug(f"Skipping refresh of frozen {name!r} on {skel['key']!r}")
            return
        super().refresh(skel, name)
