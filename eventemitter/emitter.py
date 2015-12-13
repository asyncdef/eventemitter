"""Event emitter mixin class."""

import asyncio
import collections
import contextlib
import functools
import itertools
import warnings


async def _try_catch_coro(emitter, event, listener, coro):
    """Coroutine wrapper to catch errors after async scheduling.

    Args:
        emitter (EventEmitter): The event emitter that is attempting to
            call a listener.
        event (str): The event that triggered the emitter.
        listener (async def): The async def that was used to generate the coro.
        coro (coroutine): The coroutine that should be tried.

    If an exception is caught the function will use the emitter to emit the
    failure event. If, however, the current event _is_ the failure event then
    the method reraises. The reraised exception may show in debug mode for the
    event loop but is otherwise silently dropped.
    """
    try:

        await coro

    except Exception as exc:

        if event == emitter.LISTENER_ERROR_EVENT:

            raise

        emitter.emit(emitter.LISTENER_ERROR_EVENT, event, listener, exc)


class EventEmitter:

    """A mixin that provides methods for publishing and listening to events.

    Attributes:
        DEFAULT_MAX_LISTENERS (int): The default number of listeners per
            event before the object begins emitting warnings. This value can
            be adjust by subclassing and setting this value. Alternatively, it
            can be adjusted per instance by using the max_listeners property.
            The default value is 10.
        LISTENER_ERROR_EVENT (str): The name of the event that should be
            listened to in the event of an exception within a listener.
    """

    DEFAULT_MAX_LISTENERS = 10
    LISTENER_ERROR_EVENT = 'listener-error'

    def __init__(self, loop=None):
        """Initialize the emitter with an event loop."""
        self._loop = loop or asyncio.get_event_loop()
        self._listeners = collections.defaultdict(list)
        self._once = collections.defaultdict(list)
        self._max_listeners = self.DEFAULT_MAX_LISTENERS

    def _check_limit(self, event):
        """Check if the listener limit is hit and warn if needed."""
        if self.count(event) > self.max_listeners:

            warnings.warn(
                'Too many listeners for event {}'.format(event),
                ResourceWarning,
            )

    def add_listener(self, event, listener):
        """Bind a listener to a particular event.

        Args:
            event (str): The name of the event to listen for. This may be any
                string value.
            listener (def or async def): The callback to execute when the event
                fires. This may be a sync or async function.
        """
        self.emit('new_listener', event, listener)
        self._listeners[event].append(listener)
        self._check_limit(event)
        return self

    on = add_listener

    def once(self, event, listener):
        """Add a listener that is only called once."""
        self.emit('new_listener', event, listener)
        self._once[event].append(listener)
        self._check_limit(event)
        return self

    def remove_listener(self, event, listener):
        """Remove a listener from the emitter.

        Args:
            event (str): The event name on which the listener is bound.
            listener: A reference to the same object given to add_listener.

        Returns:
            bool: True if a listener was removed else False.

        This method only removes one listener at a time. If a listener is
        attached multiple times then this method must be called repeatedly.
        Additionally, this method removes listeners first from the those
        registered with 'on' or 'add_listener'. If none are found it continue
        to remove afterwards from those added with 'once'.
        """
        with contextlib.suppress(ValueError):

            self._listeners[event].remove(listener)
            return True

        with contextlib.suppress(ValueError):

            self._once[event].remove(listener)
            return True

        return False

    def remove_all_listeners(self, event=None):
        """Remove all listeners, or those of the specified *event*.

        It's not a good idea to remove listeners that were added elsewhere in
        the code, especially when it's on an emitter that you didn't create
        (e.g. sockets or file streams).
        """
        if event is None:
            self._listeners = collections.defaultdict(list)
            self._once = collections.defaultdict(list)
        else:
            del self._listeners[event]
            del self._once[event]

    @property
    def max_listeners(self):
        """Get the max number of listeners before warning."""
        return self._max_listeners

    @max_listeners.setter
    def max_listeners(self, value):
        """Set the max number of listeners before warning."""
        self._max_listeners = value

    def listeners(self, event):
        """Get an iterable of all listeners for the given event.

        Args:
            event (str): The name of the event for which to generate an
                iterable of listeners.

        The resulting iterable contains all listeners regardless of whether
        they were registered with 'on'/'add_listener' or 'once'.
        """
        return self._listeners[event][:] + self._once[event][:]

    def _dispatch_coroutine(self, event, listener, *args, **kwargs):
        """Schedule a coroutine for execution.

        Args:
            event (str): The name of the event that triggered this call.
            listener (async def): The async def that needs to be executed.
            *args: Any number of positional arguments.
            **kwargs: Any number of keyword arguments.

        The values of *args and **kwargs are passed, unaltered, to the async
        def when generating the coro. If there is an exception generating the
        coro, such as the wrong number of arguments, the emitter's error event
        is triggered. If the triggering event _is_ the emitter's error event
        then the exception is reraised. The reraised exception may show in
        debug mode for the event loop but is otherwise silently dropped.
        """
        try:

            coro = listener(*args, **kwargs)

        except Exception as exc:

            if event == self.LISTENER_ERROR_EVENT:

                raise

            return self.emit(self.LISTENER_ERROR_EVENT, event, listener, exc)

        asyncio.ensure_future(
            _try_catch_coro(self, event, listener, coro),
            loop=self._loop,
        )

    def _dispatch_function(self, event, listener, *args, **kwargs):
        """Execute a sync function.

        Args:
            event (str): The name of the event that triggered this call.
            listener (def): The def that needs to be executed.
            *args: Any number of positional arguments.
            **kwargs: Any number of keyword arguments.

        The values of *args and **kwargs are passed, unaltered, to the def
        when exceuting. If there is an exception executing the def, such as the
        wrong number of arguments, the emitter's error event is triggered. If
        the triggering event _is_ the emitter's error event then the exception
        is reraised. The reraised exception may show in debug mode for the
        event loop but is otherwise silently dropped.
        """
        try:

            return listener(*args, **kwargs)

        except Exception as exc:

            if event == self.LISTENER_ERROR_EVENT:

                raise

            return self.emit(self.LISTENER_ERROR_EVENT, event, listener, exc)

    def _dispatch(self, event, listener, *args, **kwargs):
        """Dispatch an event to a listener.

        Args:
            event (str): The name of the event that triggered this call.
            listener (def or async def): The listener to trigger.
            *args: Any number of positional arguments.
            **kwargs: Any number of keyword arguments.

        This method inspects the listener. If it is a def it dispatches the
        listener to a method that will execute that def. If it is an async def
        it dispatches it to a method that will schedule the resulting coro with
        the event loop.
        """
        if (
            asyncio.iscoroutinefunction(listener) or
            isinstance(listener, functools.partial) and
            asyncio.iscoroutinefunction(listener.func)
        ):

            return self._dispatch_coroutine(event, listener, *args, **kwargs)

        return self._dispatch_function(event, listener, *args, **kwargs)

    def emit(self, event, *args, **kwargs):
        """Call each listener for the event with the given arguments.

        Args:
            event (str): The event to trigger listeners on.
            *args: Any number of positional arguments.
            **kwargs: Any number of keyword arguments.

        This method passes all arguments other than the event name directly
        to the listeners. If a listener raises an exception for any reason the
        'listener-error', or current value of LISTENER_ERROR_EVENT, is emitted.
        Listeners to this event are given the event name, listener object, and
        the exception raised. If an error listener fails it does so silently.

        All event listeners are fired in a deferred way so this method returns
        immediately. The calling coro must yield at some point for the event
        to propagate to the listeners.
        """
        listeners = self._listeners[event]
        listeners = itertools.chain(listeners, self._once[event])
        self._once[event] = []
        for listener in listeners:

            self._loop.call_soon(
                functools.partial(
                    self._dispatch,
                    event,
                    listener,
                    *args,
                    **kwargs,
                )
            )

        return self

    def count(self, event):
        """Get the number of listeners for the event.

        Args:
            event (str): The event for which to count all listeners.

        The resulting count is a combination of listeners added using
        'on'/'add_listener' and 'once'.
        """
        return len(self._listeners[event]) + len(self._once[event])
