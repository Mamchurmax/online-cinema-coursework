"""Builds the event bus for one unit of work (one request or script run).

All observers are subscribed here, so this file is the single place that shows
who reacts to which event.
"""

from sqlalchemy.orm import Session

from app.repositories.catalog_repository import TitleRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.events.bus import EventBus
from app.services.events.events import (
    PaymentFailed,
    PaymentSucceeded,
    SubscriptionActivated,
    SubscriptionExpiring,
    TitleWatched,
)
from app.services.events.listeners import NotificationListener, StatisticsListener
from app.services.notifications.notification_service import NotificationService


def build_event_bus(db: Session) -> EventBus:
    bus = EventBus()

    statistics = StatisticsListener(TitleRepository(db))
    bus.subscribe(TitleWatched, statistics.on_title_watched)

    notifications = NotificationListener(NotificationService(NotificationRepository(db)))
    bus.subscribe(PaymentSucceeded, notifications.on_payment_succeeded)
    bus.subscribe(PaymentFailed, notifications.on_payment_failed)
    bus.subscribe(SubscriptionActivated, notifications.on_subscription_activated)
    bus.subscribe(SubscriptionExpiring, notifications.on_subscription_expiring)

    return bus
