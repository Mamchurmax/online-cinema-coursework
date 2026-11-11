"""Enumerations used by the domain models."""

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class TitleType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentScenario(StrEnum):
    """Outcome the user picks on the mock payment page."""

    SUCCESS = "success"
    PENDING = "pending"
    FAILED = "failed"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NotificationType(StrEnum):
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
