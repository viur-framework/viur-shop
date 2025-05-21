"""
Event Handling Module
=====================

This module provides a flexible and extensible event-handling system that
allows methods to be attached to specific events.
These methods are triggered when the corresponding events occur,
enabling custom behavior and seamless integration of additional functionality
into the application workflow.

Key Components
--------------

1. **Event Enum**
   Defines the set of events that can be triggered in the system.
   These events act as unique identifiers for specific points in the order's lifecycle.
   For example:

   - ``CHECKOUT_STARTED``: Triggered when a checkout process starts.
   - ``ORDER_ORDERED``: Triggered when an order is created.
   - ``ORDER_PAID``: Triggered when an order is paid.
   - ``ORDER_RTS``: Triggered when an order is ready to ship.

2. **EventService**
   Manages the registration, unregistration, and invocation of event-handling methods.

   - **Registration**: Use ``register()`` to associate a function with a specific event.
   - **Unregistration**: Use ``unregister()`` to detach a function from an event.
   - **Invocation**: Use ``call()`` to trigger all functions associated with an event,
     passing any required arguments.

3. **on_event Decorator**
   A convenient decorator for attaching methods to specific events.
   This provides a clear and concise way to define event-driven behavior.

Usage
-----

Registering an Event Handler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can register an event handler manually or use the ``@on_event`` decorator.

.. code-block:: python

   from viur.shop.services import Event, on_event

   # Using the decorator
   @on_event(Event.CHECKOUT_STARTED)
   def notify_user_on_checkout(order_skel):
       print(f"Checkout started with skel: {order_skel}")

   # Registering manually
   EVENT_SERVICE.register(Event.ORDER_PAID, process_payment)

Triggering an Event
~~~~~~~~~~~~~~~~~~~

To trigger an event and execute all associated methods,
use the ``call`` method of ``EventService``.

.. code-block:: python

   from viur.shop.services import Event, on_event

   EVENT_SERVICE.call(Event.CHECKOUT_STARTED, order_skel=order_skel)

Error Handling
--------------

The ``call()`` method includes an ``_raise_errors`` parameter to control
whether exceptions should propagate or be suppressed.

Overview
--------

This module simplifies event-driven programming by decoupling event producers
and consumers, allowing developers to extend the application without modifying
its core logic.
"""

import collections
import enum
import typing as t

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Event(enum.IntEnum):
    """
    Defines the available events used within the system.

    This enumeration serves as the central registry for all predefined events
    that can be triggered and observed by the `EventService`.
    """

    ARTICLE_CHANGED = enum.auto()
    """Triggered when an article inside the cart (leaf) changed."""

    CART_CHANGED = enum.auto()
    """Triggered when a cart (node) changed."""

    ORDER_CHANGED = enum.auto()
    """Triggered when an order changed."""

    CHECKOUT_STARTED = enum.auto()
    """Triggered when a user begins the checkout process."""

    ORDER_ORDERED = enum.auto()
    """Triggered when a user confirmed the order ("order now") in the final checkout step."""

    ORDER_PAID = enum.auto()
    """Triggered when payment for an order is completed."""

    ORDER_RTS = enum.auto()
    """Triggered when an order is marked as ready to ship (RTS)."""


class EventService:
    observer: t.Final[dict[[Event, list[t.Callable]]]] = collections.defaultdict(list)

    def register(self, event: Event, func: t.Callable) -> t.Callable:
        if not isinstance(event, Event):
            raise TypeError(f"event must be of type Event")
        EventService.observer[event].append(func)
        return func

    def unregister(self, func: t.Callable, event: Event = None) -> None:
        for event_, funcs in EventService.observer:
            if event is None or event_ == Event:
                try:
                    funcs.pop(func, )
                except ValueError:
                    pass

    def call(
        self,
        _event: Event,
        _raise_errors: bool = False,
        *args, **kwargs
    ) -> None:
        for func in EventService.observer[_event]:
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error while calling {func} at event {_event!r}: {e}")
                if _raise_errors:
                    raise e


EVENT_SERVICE = EventService()


def on_event(event: Event) -> t.Callable:
    if not isinstance(event, Event):
        raise TypeError

    def outer_wrapper(func: t.Callable) -> t.Callable:
        EVENT_SERVICE.register(event, func)
        return func

    return outer_wrapper
