import logging
import time
import typing as t  # noqa

import datetime

from viur import toolkit
from viur.core import current, db, errors as core_errors, exposed, force_post, utils
from viur.core.prototypes import List
from viur.shop.types import *
from viur.shop.types.results import PaymentProviderResult
from .abstract import ShopModuleAbstract
from ..globals import SENTINEL, SHOP_LOGGER
from ..payment_providers import PaymentProviderAbstract
from ..services import EVENT_SERVICE, Event, HOOK_SERVICE, Hook
from ..skeletons.order import OrderSkel
from ..types import error_handler, exceptions as e

if t.TYPE_CHECKING:
    from viur.core.skeleton import SkeletonInstance

logger = SHOP_LOGGER.getChild(__name__)


class Order(ShopModuleAbstract, List):
    moduleName = "order"
    kindName = "{{viur_shop_modulename}}_order"

    reference_user_created_skeletons_in_session = True

    def adminInfo(self) -> dict:
        admin_info = super().adminInfo()
        return admin_info | {
            "icon": "cart-check",
            "filter": {
                "orderby": "creationdate",
                "orderdir": 1,  # Descending
            }
        }

    # --- Session -------------------------------------------------------------

    @property
    def current_session_order_key(self) -> db.Key | None:
        return self.session.get("session_order_key")

    @current_session_order_key.setter
    def current_session_order_key(self, value: db.Key) -> None:
        self.session["session_order_key"] = value
        current.session.get().markChanged()

    @property
    def current_order_skel(self) -> SkeletonInstance_T[OrderSkel] | None:
        if not self.current_session_order_key:
            return None
        return self.order_get(self.current_session_order_key)

    # --- ViUR ----------------------------------------------------------------

    def canView(self, skel: "SkeletonInstance") -> bool:
        if super().canView(skel):
            return True

        if skel["key"] in self.session.get("created_skel_keys", ()):
            logger.debug(f"User added this order in his session: {skel['key']!r}")
            return True

        return False

    # --- (internal) API methods ----------------------------------------------

    @exposed
    def payment_providers_list(  # TODO(discuss): Move: to API?
        self,
        only_available: bool = True,
    ) -> JsonResponse[dict[str, PaymentProviderResult]]:
        """
        Get a list of payment providers.

        This method returns a JSON response containing a dictionary of payment
        providers. The keys represent provider identifiers, and the values are
        instances of `PaymentProviderResult` (dict) containing the details of each provider.

        :param only_available: If ``True`` (default), only payment providers that
            are currently available will be included in the response.
            If ``False``, all providers will be listed regardless of availability.
        :return: A JSON response with a dictionary of payment providers.
        """
        return JsonResponse(self.get_payment_providers(only_available))

    def get_payment_providers(
        self,
        only_available: bool = True,
    ) -> dict[str, PaymentProviderResult]:
        order_skel = self.current_order_skel  # Evaluate property only once
        res: dict[str, PaymentProviderResult] = {
            pp.name: pp.serialize_for_api(order_skel)
            for pp in self.shop.payment_providers
        }
        if only_available:
            return {name: result for name, result in res.items()
                    if result["is_available"]}
        return res

    def order_get(
        self,
        order_key: db.Key,
    ) -> SkeletonInstance_T[OrderSkel] | None:
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        skel = self.viewSkel()
        if not skel.read(order_key):
            logger.debug(f"Order {order_key} does not exist")
            return None
        if not self.canView(skel):
            logger.debug(f"Order {order_key} is forbidden by canView")
            return None
        return skel

    def order_add(
        self,
        cart_key: db.Key,
        payment_provider: str = SENTINEL,
        billing_address_key: db.Key = SENTINEL,
        customer_key: db.Key = SENTINEL,
        state_ordered: bool = SENTINEL,
        state_paid: bool = SENTINEL,
        state_rts: bool = SENTINEL,
        **kwargs,
    ):
        if not isinstance(cart_key, db.Key):
            raise TypeError(f"cart_key must be an instance of db.Key")
        if billing_address_key is not SENTINEL and not isinstance(billing_address_key, (db.Key, type(None))):
            raise TypeError(f"billing_address_key must be an instance of db.Key")
        if customer_key is not SENTINEL and not isinstance(customer_key, (db.Key, type(None))):
            raise TypeError(f"customer_key must be an instance of db.Key")
        skel = self.addSkel()
        cart_skel = self.shop.cart.viewSkel("node")
        if not self.shop.cart.is_valid_node(cart_key, root_node=True):
            raise e.InvalidArgumentException(
                "cart_key",
                cart_key,
                "cart_key is not a valid root cart for the current user",
            )
        assert cart_skel.read(cart_key)
        skel.setBoneValue("cart", cart_key)
        skel["total"] = cart_skel["total_discount_price"]
        if user := current.user.get():
            # use current user as default value
            skel.setBoneValue("customer", user["key"])
        # Initialize list for payment attempts / partial payments
        if not skel["payment"]:
            skel["payment"] = {}
        skel["payment"].setdefault("payments", [])
        skel = self._order_set_values(
            skel,
            payment_provider=payment_provider,
            billing_address_key=billing_address_key,
            customer_key=customer_key,
            state_ordered=state_ordered,
            state_paid=state_paid,
            state_rts=state_rts,
        )
        try:
            skel = HOOK_SERVICE.dispatch(Hook.ORDER_ADD_ADDITION)(skel)
        except DispatchError:
            pass
        skel = self.additional_order_add(skel, **kwargs)
        self.onAdd(skel)
        skel.write()
        self.current_session_order_key = skel["key"]
        self.onAdded(skel)
        EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=skel, deleted=False)
        return skel

    def order_update(
        self,
        order_key: db.Key,
        payment_provider: str = SENTINEL,
        billing_address_key: db.Key = SENTINEL,
        customer_key: db.Key = SENTINEL,
        state_ordered: bool = SENTINEL,
        state_paid: bool = SENTINEL,
        state_rts: bool = SENTINEL,
        **kwargs,
    ):
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        if billing_address_key is not SENTINEL and not isinstance(billing_address_key, (db.Key, type(None))):
            raise TypeError(f"billing_address_key must be an instance of db.Key")
        if customer_key is not SENTINEL and not isinstance(customer_key, (db.Key, type(None))):
            raise TypeError(f"customer_key must be an instance of db.Key")
        skel = self.editSkel()
        if not skel.read(order_key):
            raise core_errors.NotFound
        skel = self._order_set_values(
            skel,
            payment_provider=payment_provider,
            billing_address_key=billing_address_key,
            customer_key=customer_key,
            state_ordered=state_ordered,
            state_paid=state_paid,
            state_rts=state_rts,
        )
        try:
            skel = HOOK_SERVICE.dispatch(Hook.ORDER_UPDATE_ADDITION)(skel)
        except DispatchError:
            pass
        skel = self.additional_order_update(skel, **kwargs)
        OrderSkel.refresh_cart(skel)
        self.onEdit(skel)
        skel.write()
        self.onEdited(skel)
        EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=skel, deleted=False)
        return skel

    def _order_set_values(
        self,
        skel: SkeletonInstance_T[OrderSkel],
        *,
        payment_provider: str = SENTINEL,
        billing_address_key: db.Key = SENTINEL,
        customer_key: db.Key = SENTINEL,
        state_ordered: bool = SENTINEL,
        state_paid: bool = SENTINEL,
        state_rts: bool = SENTINEL,
    ) -> SkeletonInstance_T[OrderSkel]:
        if payment_provider is not SENTINEL:
            if payment_provider is not None and payment_provider not in self.get_payment_providers(True):
                raise e.InvalidArgumentException("payment_provider")
            skel["payment_provider"] = payment_provider
        if billing_address_key is not SENTINEL:
            if billing_address_key is None:
                skel["billing_address"] = None
            else:
                skel.setBoneValue("billing_address", billing_address_key)
                if AddressType.BILLING.value not in (
                    addr.value for addr in skel["billing_address"]["dest"]["address_type"]
                ):
                    raise e.InvalidArgumentException(
                        "billing_address",
                        descr_appendix="Address is not of type billing."
                    )
        if user := current.user.get():
            # use current user as default value
            skel.setBoneValue("customer", user["key"])
        if customer_key is not SENTINEL:
            if not self.customer_is_valid(skel, customer_key):
                raise e.InvalidArgumentException("customer_key")
            skel.setBoneValue("customer", customer_key)

        if state_ordered != SENTINEL or state_paid != SENTINEL or state_rts != SENTINEL:
            # any of these values should be set
            if not self.canEdit(skel):
                raise core_errors.Forbidden("You are not allowed to change a state")
            logger.debug("Can change states")
        if state_ordered is not SENTINEL:
            skel["state_ordered"] = state_ordered
        if state_paid is not SENTINEL:
            skel["state_paid"] = state_paid
        if state_rts is not SENTINEL:
            skel["state_rts"] = state_rts

        return skel

    def customer_is_valid(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
        customer_key: db.Key,
    ) -> bool:
        """Checks if the given customer is a valid customer for this skel.

        The customer must be the same user or an root user.
        """
        if not (user := current.user.get()):
            return False
        if user["key"] == customer_key:  # customer == current user
            return True
        return toolkit.user_has_access("root")  # other user

    @exposed
    @force_post
    @error_handler
    def checkout_start(
        self,
        order_key: db.Key,
    ):
        """
        Start the checkout process.

        Requires no errors in :meth:`self.can_checkout`.
        """
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        order_skel = self.editSkel()
        if not order_skel.read(order_key):
            raise core_errors.NotFound()
        order_skel.refresh()  # TODO: cart.shipping_address relation seems not be updated by the core
        if ClientError.has_failing_error(errors := self.can_checkout(order_skel)):
            logging.error(errors)
            return JsonResponse({
                "errors": errors,
            }, status_code=400)

        order_skel = self.freeze_order(order_skel)
        try:
            order_skel = HOOK_SERVICE.dispatch(Hook.ORDER_CHECKOUT_START_ADDITION)(order_skel)
        except DispatchError:
            pass
        order_skel.write()
        self.set_checkout_in_progress(order_skel)

        # Detach only after the checkout start succeeded completely:
        # if freeze or write fails, the user keeps their session cart --
        # detaching first would leave them with an empty new basket while
        # the old cart dangles half-frozen behind the failed order.
        if order_skel["cart"]["dest"]["key"] == self.shop.cart.current_session_cart_key:
            # This is now an order basket and should no longer be modified
            self.shop.cart.detach_session_cart()

        EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)
        return JsonResponse({
            "skel": order_skel,
            "payment": (self.get_payment_provider_by_name(order_skel["payment_provider"])
                        .get_checkout_start_data(order_skel)),
        })

    def can_checkout(
        self,
        order_skel: "SkeletonInstance",
    ) -> list[ClientError]:
        errors = []
        if not order_skel["cart"]:
            errors.append(ClientError("cart is missing"))
        if not order_skel["billing_address"]:
            errors.append(ClientError("billing_address is missing"))
        # Note: payment_provider el-if
        if not order_skel["payment_provider"]:
            errors.append(ClientError("missing payment_provider"))
        elif pp_errors := self.get_payment_provider_by_name(order_skel["payment_provider"]).can_checkout(order_skel):
            errors.extend(pp_errors)
        # TODO: ensure each article still exists and shop_listed is True

        # TODO: ...
        return errors

    def freeze_order(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
    ) -> SkeletonInstance_T[OrderSkel]:
        cart_skel = self.shop.cart.freeze_cart(order_skel["cart"]["dest"]["key"])
        order_skel["total"] = cart_skel["total_discount_price"]

        # Clone the address, so in case the user edits the address, existing orders wouldn't be affected by this
        # TODO: Can we do this copy-on-write instead; clone if an address is edited and replace on used order skels?
        ba_key = order_skel["billing_address"]["dest"]["key"]
        ba_skel = self.shop.address.clone_address(ba_key)
        assert ba_skel["key"] != ba_key, f'{ba_skel["key"]} != {ba_key}'
        order_skel.setBoneValue("billing_address", ba_skel["key"])
        order_skel.write()
        EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)

        return order_skel

    def _default_assign_uid(
        self,
        order_skel: "SkeletonInstance",
    ) -> "SkeletonInstance":
        """Default order assign id method.

        Called as default/fallback for :attr:`Hook.ORDER_ASSIGN_UID`.
        """
        order_skel = toolkit.set_status(
            key=order_skel["key"],
            skel=order_skel,
            values={
                "order_uid": "".join(
                    f"-{c}" if i % 4 == 0 else c
                    for i, c in enumerate(str(time.time()).replace(".", ""))
                ).strip("-"),
            },
        )
        return order_skel

    @exposed
    @force_post
    @error_handler
    def checkout_order(
        self,
        order_key: db.Key,
    ):
        """
        The final order now step.

        Requires no errors in :meth:`self.can_order`.
        """
        order_key = self.shop.api._normalize_external_key(order_key, "order_key")
        if not isinstance(order_key, db.Key):
            raise TypeError(f"order_key must be an instance of db.Key")
        order_skel = self.editSkel()
        if not order_skel.read(order_key):
            raise core_errors.NotFound()

        if ClientError.has_failing_error(errors := self.can_order(order_skel)):
            logging.error(errors)
            return JsonResponse({
                "errors": errors,
            }, status_code=400)

        # Claim the order before talking to the payment provider: a repeated
        # checkout_order call (double click, crash between the provider call
        # and set_ordered, replayed request) must not trigger a second charge.
        try:
            order_skel = self._claim_checkout_order(order_skel)
        except e.InvalidStateError as exc:
            logging.warning(f"Rejecting checkout_order for {order_key!r}: {exc}")
            return JsonResponse({
                "errors": [ClientError("checkout_order is already in progress")],
            }, status_code=409)

        try:
            order_skel = HOOK_SERVICE.dispatch(Hook.ORDER_ASSIGN_UID, self._default_assign_uid)(order_skel)
            # TODO: charge order if it should directly be charged
            pp_res = self.get_payment_provider_by_name(order_skel["payment_provider"]).checkout(order_skel)
        except Exception:
            # Release the claim, the user may retry immediately
            toolkit.set_status(
                key=order_skel["key"],
                skel=order_skel,
                values={"checkout_order_started": None},
            )
            raise
        order_skel = self.set_ordered(order_skel, pp_res)
        EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)
        return JsonResponse({
            "skel": order_skel,
            "payment": pp_res,
        })

    CHECKOUT_ORDER_CLAIM_TIMEOUT: t.Final[datetime.timedelta] = datetime.timedelta(minutes=15)
    """How long a `checkout_order` claim blocks further attempts.

    If a claimed checkout neither completed (``is_ordered``) nor released its
    claim (crash between the payment provider call and :meth:`set_ordered`),
    a new attempt is allowed after this period."""

    def _claim_checkout_order(
        self,
        order_skel: SkeletonInstance_T[OrderSkel],
    ) -> SkeletonInstance_T[OrderSkel]:
        """
        Mark the order as "checkout_order in progress".

        Sets ``checkout_order_started`` to now, guarded by a precondition:
        already ordered orders and orders with a non-expired claim are
        rejected with :exc:`InvalidStateError`.  Together with
        `toolkit.set_status` this makes the claim a check-and-set --
        the payment provider gets called at most once per claim period,
        preventing double charges.

        :param order_skel: Skeleton of the order to claim.
        :return: The updated order skeleton.
        :raises InvalidStateError: If the order is already ordered or claimed.
        """

        def precondition(skel: "SkeletonInstance") -> None:
            if skel["is_ordered"]:
                raise e.InvalidStateError("Order already is_ordered")
            if (started := skel["checkout_order_started"]) is not None:
                if utils.utcNow() - started < self.CHECKOUT_ORDER_CLAIM_TIMEOUT:
                    raise e.InvalidStateError(f"checkout_order already started at {started.isoformat()}")
                logging.warning(f'Overtaking expired checkout_order claim from {started.isoformat()} '
                                f'of order {skel["key"]!r}')

        return toolkit.set_status(
            key=order_skel["key"],
            skel=order_skel,
            precondition=precondition,
            values={"checkout_order_started": utils.utcNow()},
        )

    def can_order(
        self,
        order_skel: "SkeletonInstance",
    ) -> list[ClientError]:
        errors = []
        if order_skel["is_ordered"]:
            errors.append(ClientError("already is_ordered"))
        if not order_skel["cart"]:
            errors.append(ClientError("cart is missing"))
        if not order_skel["cart"] or not order_skel["cart"]["dest"]["shipping_address"]:
            errors.append(ClientError("cart.shipping_address is missing"))
        if not order_skel["cart"] or not order_skel["cart"]["dest"]["total_quantity"]:
            errors.append(ClientError("cart.total_quantity is zero"))
        if not order_skel["billing_address"]:
            errors.append(ClientError("billing_address is missing"))
        if not order_skel["billing_address"] or not order_skel["billing_address"]["dest"]["email"]:
            errors.append(ClientError("email is missing"))
        if not order_skel["billing_address"] or not order_skel["billing_address"]["dest"]["phone"]:
            address_skel = order_skel.billing_address._refSkelCache()
            errors.append(ClientError(
                "phone is missing",
                # Phone number can be enforced by setting the whole bone required or soft-required via params.
                causes_failure=address_skel.phone.required or address_skel.phone.params.get("required") or False,
            ))
        # Note: payment_provider el-if
        if not order_skel["payment_provider"]:
            errors.append(ClientError("missing payment_provider"))
        elif pp_errors := self.get_payment_provider_by_name(order_skel["payment_provider"]).can_order(order_skel):
            errors.extend(pp_errors)

        # TODO: ...
        return errors

    def set_checkout_in_progress(self, order_skel: "SkeletonInstance") -> "SkeletonInstance":
        """Set an order to the state *is_checkout_in_progress*"""
        order_skel = toolkit.set_status(
            key=order_skel["key"],
            skel=order_skel,
            values={"is_checkout_in_progress": True},
        )
        EVENT_SERVICE.call(Event.CHECKOUT_STARTED, order_skel=order_skel)
        EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)
        return order_skel

    def _set_state_once(
        self,
        order_skel: "SkeletonInstance",
        state_bone: str,
    ) -> tuple["SkeletonInstance", bool]:
        """
        Set a boolean state bone of an order to ``True`` exactly once.

        Uses a `set_status` precondition, so the check and the write happen
        in the same read-modify-write cycle: if the state is already set
        (e.g. by a concurrently processed payment webhook), nothing is
        written and the caller gets ``False`` -- it then must not fire the
        state's events again, keeping side effects like mails or discount
        accounting from running twice.

        :param order_skel: Skeleton of the order to modify.
        :param state_bone: Name of the boolean state bone (e.g. ``is_paid``).
        :return: Tuple of the (possibly updated) skeleton and whether this
            call actually performed the transition.
        """

        def precondition(skel: "SkeletonInstance") -> None:
            if skel[state_bone]:
                raise e.InvalidStateError(f"Order already has {state_bone} set")

        try:
            order_skel = toolkit.set_status(
                key=order_skel["key"],
                skel=order_skel,
                precondition=precondition,
                values={state_bone: True},
            )
        except e.InvalidStateError:
            logger.info(f'Order {order_skel["key"]!r} already has {state_bone} set; skipping transition')
            return order_skel, False
        return order_skel, True

    def set_ordered(self, order_skel: "SkeletonInstance", payment: t.Any) -> "SkeletonInstance":
        """Set an order to the state *ordered*.

        Idempotent: the ``ORDER_ORDERED`` event fires only on the actual
        transition, a repeated call changes and triggers nothing.
        """
        order_skel, changed = self._set_state_once(order_skel, "is_ordered")
        if changed:
            EVENT_SERVICE.call(Event.ORDER_ORDERED, order_skel=order_skel, payment=payment)
            EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)
        return order_skel

    def set_paid(self, order_skel: "SkeletonInstance") -> "SkeletonInstance":
        """Set an order to the state *paid*.

        Idempotent: the ``ORDER_PAID`` event fires only on the actual
        transition, a repeated call (e.g. return handler and payment
        webhook processing the same payment) changes and triggers nothing.
        """
        order_skel, changed = self._set_state_once(order_skel, "is_paid")
        if changed:
            EVENT_SERVICE.call(Event.ORDER_PAID, order_skel=order_skel)
            EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)
        return order_skel

    def set_rts(self, order_skel: "SkeletonInstance") -> "SkeletonInstance":
        """Set an order to the state *Ready to ship*.

        Idempotent: the ``ORDER_RTS`` event fires only on the actual
        transition, a repeated call changes and triggers nothing.
        """
        order_skel, changed = self._set_state_once(order_skel, "is_rts")
        if changed:
            EVENT_SERVICE.call(Event.ORDER_RTS, order_skel=order_skel)
            EVENT_SERVICE.call(Event.ORDER_CHANGED, order_skel=order_skel, deleted=False)
        return order_skel

    # --- Hooks ---------------------------------------------------------------

    def additional_order_add(
        self,
        skel: SkeletonInstance_T[OrderSkel],
        /,
        **kwargs,
    ) -> SkeletonInstance_T[OrderSkel]:
        """
        Hook method called by :meth:`order_add` before the skeleton is saved.

        This method can be overridden in a subclass to implement additional API fields or
        make further modifications to the order skeleton (`skel`).
        By default, it raises an exception if unexpected arguments
        (``kwargs``) are provided and returns the unchanged `skel` object.

        :param skel: The current instance of the order skeleton.
        :param kwargs: Additional optional arguments for extended implementations.
        :raises TooManyArgumentsException: If unexpected arguments are passed in ``kwargs``.
        :return: The (potentially modified) order skeleton.
        """
        if kwargs:
            raise e.TooManyArgumentsException(f"{self}.order_add", *kwargs.keys())
        return skel

    def additional_order_update(
        self,
        skel: SkeletonInstance_T[OrderSkel],
        /,
        **kwargs,
    ) -> SkeletonInstance_T[OrderSkel]:
        """
        Hook method called by :meth:`order_update` before the skeleton is saved.

        This method can be overridden in a subclass to implement additional API fields or
        make further modifications to the order skeleton (`skel`).
        By default, it raises an exception if unexpected arguments
        (``kwargs``) are provided and returns the unchanged `skel` object.

        :param skel: The current instance of the order skeleton.
        :param kwargs: Additional optional arguments for extended implementations.
        :raises TooManyArgumentsException: If unexpected arguments are passed in ``kwargs``.
        :return: The (potentially modified) order skeleton.
        """
        if kwargs:
            raise e.TooManyArgumentsException(f"{self}.order_update", *kwargs.keys())
        return skel

    # --- Internal helpers  ----------------------------------------------------

    def get_payment_provider_by_name(
        self,
        payment_provider_name: str,
    ) -> PaymentProviderAbstract:
        for pp in self.shop.payment_providers:
            if payment_provider_name == pp.name:
                return pp
        raise LookupError(f"Unknown payment provider {payment_provider_name}")
