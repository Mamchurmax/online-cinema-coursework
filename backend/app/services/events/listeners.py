"""Observers of domain events. Each listener does one job (Single Responsibility)."""

from datetime import datetime
from decimal import Decimal

from app.models import NotificationType
from app.repositories.catalog_repository import TitleRepository
from app.services.events.events import (
    DomainEvent,
    PaymentFailed,
    PaymentSucceeded,
    SubscriptionActivated,
    SubscriptionExpiring,
    TitleWatched,
)
from app.services.notifications.notification_service import NotificationService


class StatisticsListener:
    """Counts finished views per title (used by popularity reports and recommendations)."""

    def __init__(self, titles: TitleRepository) -> None:
        self._titles = titles

    def on_title_watched(self, event: DomainEvent) -> None:
        assert isinstance(event, TitleWatched)
        self._titles.increment_watch_count(event.title_id)


def _date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def _money(amount: Decimal) -> str:
    return f"{amount:.2f} грн"


class NotificationListener:
    """Turns billing events into notifications for the user."""

    def __init__(self, notifications: NotificationService) -> None:
        self._notifications = notifications

    def on_payment_succeeded(self, event: DomainEvent) -> None:
        assert isinstance(event, PaymentSucceeded)
        self._notifications.notify(
            event.user_id,
            NotificationType.PAYMENT_SUCCEEDED,
            f"Оплату {_money(event.amount)} отримано. Дякуємо!",
        )

    def on_payment_failed(self, event: DomainEvent) -> None:
        assert isinstance(event, PaymentFailed)
        self._notifications.notify(
            event.user_id,
            NotificationType.PAYMENT_FAILED,
            "Оплата не пройшла. Спробуйте ще раз або оберіть інший спосіб оплати.",
        )

    def on_subscription_activated(self, event: DomainEvent) -> None:
        assert isinstance(event, SubscriptionActivated)
        self._notifications.notify(
            event.user_id,
            NotificationType.SUBSCRIPTION_ACTIVATED,
            f"Підписку {event.plan_name} активовано до {_date(event.expires_at)}.",
        )

    def on_subscription_expiring(self, event: DomainEvent) -> None:
        assert isinstance(event, SubscriptionExpiring)
        days = event.days_left
        when = "сьогодні" if days <= 0 else "завтра" if days == 1 else f"через {days} дн."
        self._notifications.notify(
            event.user_id,
            NotificationType.SUBSCRIPTION_EXPIRING,
            f"Підписка {event.plan_name} закінчується {when} ({_date(event.expires_at)}). "
            "Продовжте її, щоб дивитися без реклами.",
        )
