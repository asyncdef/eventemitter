"""Async iterable that wraps an EventEmitter."""

import asyncio
import collections
from collections.abc import AsyncIterator, AsyncIterable


class EventIterator(AsyncIterator):

    """An iterator who values are the payloads from emitted events."""

    def __init__(self, emitter, event):
        """Initialize the iterator with an emitter and event to fire on."""
        self._emitter = emitter
        self._event = event
        self._emitter.on(event, self._push)
        self._data = collections.deque()
        self._future = None

    async def _push(self, *args, **kwargs):
        """Push new data into the buffer. Resume looping if paused."""
        self._data.append((args, kwargs))
        if self._future is not None:

            future, self._future = self._future, None
            future.set_result(True)

    async def __anext__(self):
        """Fetch the next set of values. Wait for new values if empty."""
        if self._data:

            return self._data.popleft()

        self._future = asyncio.Future()
        await self._future
        return self._data.popleft()


class EventIterable(AsyncIterable):

    """An iterable object the iterator for which loops on each fired event."""

    def __init__(self, emitter, event):
        """Initialize the iterable with an emitter and target event."""
        self._emitter = emitter
        self._event = event

    async def __aiter__(self):
        """Get a new EventIterator object."""
        return EventIterator(self._emitter, self._event)
