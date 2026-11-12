"""Domain events published through the `EventBus` (see bus.py)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class DomainEvent:
    """Base class: listeners subscribe to concrete event classes."""


@dataclass(frozen=True)
class TitleWatched(DomainEvent):
    """A viewer has finished (90%+) a movie or an episode."""

    user_id: int
    title_id: int
    video_asset_id: int


@dataclass(frozen=True)
class PaymentSucceeded(DomainEvent):
    payment_id: int
    user_id: int
    plan_id: int
    amount: Decimal


@dataclass(frozen=True)
class PaymentFailed(DomainEvent):
    payment_id: int
    user_id: int
    plan_id: int


@dataclass(frozen=True)
class SubscriptionActivated(DomainEvent):
    subscription_id: int
    user_id: int
    plan_name: str
    expires_at: datetime


@dataclass(frozen=True)
class SubscriptionExpiring(DomainEvent):
    subscription_id: int
    user_id: int
    plan_name: str
    expires_at: datetime
    days_left: int
