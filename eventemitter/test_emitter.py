"""Test suites for the EventEmitter implementation."""

import asyncio
import functools
import warnings

from . import emitter


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
async def test_emitter_emits_async_coro():
    """Check that listeners are called async when given async def."""
    e = emitter.EventEmitter()
    value = {"touched": False}

    async def touch_value():
        """Flip the test bit to True."""
        value['touched'] = True

    e.on('test', touch_value)
    e.emit('test')
    assert value['touched'] is False
    await asyncio.sleep(0)
    assert value['touched'] is True


@async_test()
async def test_emitter_emits_async_func():
    """Check that listeners are called async when given def."""
    e = emitter.EventEmitter()
    value = {"touched": False}

    def touch_value():
        """Flip the test bit to True."""
        value['touched'] = True

    e.on('test', touch_value)
    e.emit('test')
    assert value['touched'] is False
    await asyncio.sleep(0)
    assert value['touched'] is True


@async_test()
async def test_emitter_calls_multiple_times():
    """Check that listeners are called on each fired event."""
    e = emitter.EventEmitter()
    value = {'count': 0}

    def inc_value():
        """Up the counter."""
        value['count'] += 1

    e.on('test', inc_value)
    e.emit('test')
    e.emit('test')
    e.emit('test')
    await asyncio.sleep(0)
    assert value['count'] == 3


@async_test()
async def test_emitter_calls_only_once():
    """Check that once listeners are not called multiple times."""
    e = emitter.EventEmitter()
    value = {'count': 0}

    def inc_value():
        """Up the counter."""
        value['count'] += 1

    e.once('test', inc_value)
    e.emit('test')
    e.emit('test')
    e.emit('test')
    await asyncio.sleep(0)
    assert value['count'] == 1


def test_remove_listener_empty():
    """Check that False is returned when no listener is removed."""
    e = emitter.EventEmitter()
    sentinel = object()
    assert e.remove_listener('test', sentinel) is False


def test_remove_listener_full():
    """Check that True is returned when a listener is removed."""
    e = emitter.EventEmitter()
    sentinel = object()
    e.on('test', sentinel)
    assert e.remove_listener('test', sentinel) is True
    assert e.remove_listener('test', sentinel) is False


def test_remove_listener_once():
    """Check that True is returned when a once listener is removed."""
    e = emitter.EventEmitter()
    sentinel = object()
    e.once('test', sentinel)
    assert e.remove_listener('test', sentinel) is True
    assert e.remove_listener('test', sentinel) is False


def test_remove_all_listeners_for_event():
    """Check that remove_all_listeners removes all listeners for an event."""
    e = emitter.EventEmitter()

    def sync_listener():
        return True

    async def async_listener():
        await asyncio.sleep(0.001)
        return True

    e.on('test', sync_listener)
    e.on('test', async_listener)
    e.once('test', sync_listener)

    # Ensure that calling remove_all_listeners with an event name
    # leaves listeners for *other* events unaffected
    e.on('spam', sync_listener)
    e.on('spam', async_listener)
    e.once('spam', sync_listener)

    assert e.count('test') == 3
    assert e.count('spam') == 3
    e.remove_all_listeners('test')
    assert e.count('test') == 0
    assert e.count('spam') == 3


def test_remove_all_listeners():
    """Check that remove_all_listeners removes all listeners."""
    e = emitter.EventEmitter()

    def sync_listener():
        return True

    async def async_listener():
        await asyncio.sleep(0.001)
        return True

    e.on('test', sync_listener)
    e.on('test', async_listener)
    e.once('test', sync_listener)

    # Ensure that calling remove_all_listeners with no args
    # removes listeners for *all* events
    e.on('spam', sync_listener)
    e.on('spam', async_listener)
    e.once('spam', sync_listener)

    assert e.count('test') == 3
    assert e.count('spam') == 3
    e.remove_all_listeners()
    assert e.count('test') == 0
    assert e.count('spam') == 0


def test_count_shows_all_listeners():
    """Check that count returns the number of all listeners for an event."""
    e = emitter.EventEmitter()
    sentinel = object()
    e.on('test', sentinel)
    e.on('test', sentinel)
    e.once('test', sentinel)
    assert e.count('test') == 3


def test_listers_give_all():
    """Check that listeners() returns all registered listeners for event."""
    e = emitter.EventEmitter()
    sentinel = object()
    e.on('test', sentinel)
    e.on('test', sentinel)
    e.once('test', sentinel)
    listeners = e.listeners('test')
    assert len(listeners) == 3
    for listener in listeners:

        assert listener is sentinel


def test_listener_limit_warning():
    """Check that a warning is emitted if too many listeners are added."""
    e = emitter.EventEmitter()
    e.max_listeners = 1
    e.on('test', None)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        e.on('test', None)

    assert len(w) == 1
    assert issubclass(w[-1].category, ResourceWarning)
    assert "test" in str(w[-1].message)


@async_test()
async def test_listener_error_event_coro():
    """Check that the LISTENER_ERROR_EVENT is fired on async exceptions."""
    e = emitter.EventEmitter()

    async def fail(*args, **kwargs):
        """Raise an exception."""
        raise TypeError()

    caught = {'value': False}

    async def catch(event, listener, exc):
        """Catch the raised exception and assert it."""
        assert event == 'test'
        assert listener is fail
        assert isinstance(exc, TypeError)
        caught['value'] = True

    e.on('test', fail)
    e.on(e.LISTENER_ERROR_EVENT, catch)
    e.emit('test')
    while not caught['value']:

        await asyncio.sleep(0)


@async_test()
async def test_listener_error_event_coro_create():
    """Check that the LISTENER_ERROR_EVENT is fired when coro create fails."""
    e = emitter.EventEmitter()

    async def fail():
        """Rais TypeError if given any arguments."""
        return None

    caught = {'value': False}

    async def catch(event, listener, exc):
        """Catch the raised exception and assert it."""
        assert event == 'test'
        assert listener is fail
        assert isinstance(exc, TypeError)
        caught['value'] = True

    e.on('test', fail)
    e.on(e.LISTENER_ERROR_EVENT, catch)
    e.emit('test', 1, 2, 3)
    while not caught['value']:

        await asyncio.sleep(0)


@async_test()
async def test_listener_error_event_func():
    """Check that the LISTENER_ERROR_EVENT is fired on sync exceptions."""
    e = emitter.EventEmitter()

    def fail(*args, **kwargs):
        """Raise an exception."""
        raise TypeError()

    caught = {'value': False}

    def catch(event, listener, exc):
        """Catch the raised exception and assert it."""
        assert event == 'test'
        assert listener is fail
        assert isinstance(exc, TypeError)
        caught['value'] = True

    e.on('test', fail)
    e.on(e.LISTENER_ERROR_EVENT, catch)
    e.emit('test')
    while not caught['value']:

        await asyncio.sleep(0)
