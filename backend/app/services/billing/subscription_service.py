"""Subscriptions: activation after payment, expiry checks."""

import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.models import Plan, Subscription, SubscriptionStatus
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.services.events.bus import EventPublisher
from app.services.events.events import SubscriptionActivated, SubscriptionExpiring

# Users are reminded when this many days (or fewer) are left: 3 days and 1 day before.
REMINDER_DAYS = (3, 1)


class PlanNotFoundError(Exception):
    pass


class SubscriptionService:
    def __init__(
        self,
        plans: PlanRepository,
        subscriptions: SubscriptionRepository,
        events: EventPublisher,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._plans = plans
        self._subscriptions = subscriptions
        self._events = events
        self._clock = clock

    def current(self, user_id: int) -> Subscription | None:
        return self._subscriptions.get_active(user_id, self._clock())

    def activate(self, user_id: int, plan_id: int) -> Subscription:
        """Start a subscription, or extend the active one of the same plan.

        Paying again before the end adds a full period to the current end date,
        so the user never loses days they have already paid for.
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)

        now = self._clock()
        current = self._subscriptions.get_active(user_id, now)
        if current is not None and current.plan_id == plan.id:
            current.expires_at = _aware(current.expires_at) + timedelta(days=plan.period_days)
            subscription = current
        else:
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                expires_at=now + timedelta(days=plan.period_days),
            )
            self._subscriptions.add(subscription)

        self._events.publish(
            SubscriptionActivated(
                subscription_id=subscription.id,
                user_id=user_id,
                plan_name=plan.name,
                expires_at=_aware(subscription.expires_at),
            )
        )
        return subscription

    def check_expiring(self) -> tuple[int, int]:
        """Daily job: remind about soon-ending subscriptions and close ended ones.

        Returns (reminders sent, subscriptions expired).
        """
        now = self._clock()
        reminders = 0
        horizon = now + timedelta(days=max(REMINDER_DAYS))
        for subscription in self._subscriptions.list_active_expiring(now, horizon):
            days_left = math.ceil((_aware(subscription.expires_at) - now) / timedelta(days=1))
            if days_left in REMINDER_DAYS:
                reminders += 1
                self._events.publish(_expiring_event(subscription, subscription.plan, days_left))

        ended = self._subscriptions.list_ended_but_active(now)
        for subscription in ended:
            subscription.status = SubscriptionStatus.EXPIRED

        self._subscriptions.commit()
        return reminders, len(ended)


def _expiring_event(subscription: Subscription, plan: Plan, days_left: int) -> SubscriptionExpiring:
    return SubscriptionExpiring(
        subscription_id=subscription.id,
        user_id=subscription.user_id,
        plan_name=plan.name,
        expires_at=_aware(subscription.expires_at),
        days_left=days_left,
    )


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC like PostgreSQL does."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
