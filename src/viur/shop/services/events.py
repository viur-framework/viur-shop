import collections
import enum
import typing as t

from ..globals import SHOP_LOGGER

logger = SHOP_LOGGER.getChild(__name__)


class Event(enum.IntEnum):
    ORDER_STARTED = enum.auto()
    ORDER_ORDERED = enum.auto()
    ORDER_PAID = enum.auto()


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
                logger.exception(f"Error while calling {func} at event {_event}: {e}")
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
