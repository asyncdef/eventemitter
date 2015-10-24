============
eventemitter
============

*Tools for publishing and listening for events.*

Example Usage
=============

EventEmitter
------------

The `EventEmitter` class can be used directly or as a mix-in to provide the
ability to publish and subscribe to events.

.. code-block:: python

    import logging
    from eventemitter import EventEmitter

    log = logging.getLogger(__name__)
    emitter = EventEmitter()

    def log_event(event, *args, **kwargs):
        log.debug('%s %s %s', event, args, kwargs)

    emitter.on('an-event', log_event)
    emitter.emit('an-event', 1, 2, keyword=3)
    await asyncio.sleep(0)  # 'an-even (1, 2), {keyword: 3}' gets logged.

Listener functions can be defined using `def` or `async def`. All listeners are
executed in a deferred way. The coro that calls `emit` must yield for the event
to propagate.

EventIterable
-------------

If the callback-style model of listening for events is undesirable, an async
iterable is provided to offer a second model for handling events.

.. code-block:: python

    import logging
    from eventemitter import EventEmitter
    from eventemitter import EventIterable

    log = logging.getLogger(__name__)
    emitter = EventEmitter()
    iterable = EventIterable(emitter, 'an-event')

    async for args, kwargs in iterable:

        log.debug('%s %s %s', event, args, kwargs)

The `EventIterable` implements the async iterable interface and can be used in
conjunction with any of the tools in
`aitertools <https://github.com/asyncdef/aitertools>`_.

Testing
=======

All tests suites are paired one-to-one with the module they test and live
directly adjacent to that same module. All tests are expected to pass for
Python 3.5 and above. To run tests use tox with the included tox.ini file or
create a virtualenv and install the '[testing]' extras.

License
=======

    Copyright 2015 Kevin Conway

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

Contributing
============

Firstly, if you're putting in a patch then thank you! Here are some tips for
getting your patch merged:

Style
-----

As long as the code passes the PEP8 and PyFlakes gates then the style is
acceptable.

Docs
----

The PEP257 gate will check that all public methods have docstrings. If you're
adding something new, like a helper function, try out the
`napoleon style of docstrings <https://pypi.python.org/pypi/sphinxcontrib-napoleon>`_.

Tests
-----

Make sure the patch passes all the tests. If you're adding a new feature don't
forget to throw in a test or two. If you're fixing a bug then definitely add
at least one test to prevent regressions.
