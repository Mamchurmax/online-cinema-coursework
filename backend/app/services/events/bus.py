"""Pattern: Observer (GoF) — publish/subscribe for domain events.

- Subject:   `EventBus` — keeps the list of observers per event type and notifies them.
- Observers: listeners in `listeners.py` (statistics, notifications, subscription
             activation). Each one reacts to the events it subscribed to.

Publishers (`WatchHistoryService`, `PaymentService`, ...) only call `publish()`;
they do not know who listens. Adding a reaction to an event — e.g. an e-mail on a
successful payment — means writing one listener and subscribing it in `setup.py`,
without touching the publisher (Open/Closed principle).

Listeners run synchronously in the same database transaction as the publisher,
so a failure in a listener rolls the whole operation back instead of leaving
half-applied changes (e.g. a paid payment without a subscription).
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Protocol

from app.services.events.events import DomainEvent

logger = logging.getLogger(__name__)

Listener = Callable[[DomainEvent], None]


class EventPublisher(Protocol):
    """What publishers depend on: only the ability to publish."""

    def publish(self, event: DomainEvent) -> None: ...


class EventBus(EventPublisher):
    """Subject of the Observer pattern."""

    def __init__(self) -> None:
        self._listeners: dict[type[DomainEvent], list[Listener]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], listener: Listener) -> None:
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: type[DomainEvent], listener: Listener) -> None:
        self._listeners[event_type].remove(listener)

    def publish(self, event: DomainEvent) -> None:
        listeners = list(self._listeners[type(event)])
        logger.debug("Publishing %s to %d listener(s)", type(event).__name__, len(listeners))
        for listener in listeners:
            listener(event)


class NullPublisher(EventPublisher):
    """Publisher that ignores events — for scripts and tests that do not need them."""

    def publish(self, event: DomainEvent) -> None:
        pass
