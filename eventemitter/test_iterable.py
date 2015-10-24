"""Test suites for the EventIterable implementation."""

import asyncio
import functools

from . import emitter
from . import iterable


def async_test(loop=None):
    """Wrap an async test in a run_until_complete for the event loop."""
    loop = loop or asyncio.get_event_loop()

    def _outer_async_wrapper(func):
        """Closure for capturing the configurable loop."""
        @functools.wraps(func)
        def _inner_async_wrapper(*args, **kwargs):

            return loop.run_until_complete(func(*args, **kwargs))

        return _inner_async_wrapper

    return _outer_async_wrapper


@async_test()
async def test_iter_pauses_until_ready():
    """Check that the EventIterable waits until data available."""
    e = emitter.EventEmitter()
    i = iterable.EventIterable(e, 'test')
    sentinel = object()
    asyncio.get_event_loop().call_later(
        .1,
        functools.partial(e.emit, 'test', sentinel, test=sentinel),
    )
    async for args, kwargs in i:

        assert sentinel in args
        assert 'test' in kwargs
        assert kwargs['test'] is sentinel
        break


@async_test()
async def test_iter_pulls_from_buffer():
    """Check that the EventIterable emits buffered data if available."""
    e = emitter.EventEmitter()
    i = iterable.EventIterable(e, 'test')
    iterator = await i.__aiter__()
    sentinel = object()
    e.emit('test', sentinel, test=sentinel)
    await asyncio.sleep(0)
    args, kwargs = await iterator.__anext__()
    assert sentinel in args
    assert 'test' in kwargs
    assert kwargs['test'] is sentinel
