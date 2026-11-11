"""ORM models. Importing this package registers every table in `Base.metadata`."""

from app.models.activity import Favorite, Notification, WatchHistory
from app.models.base import Base
from app.models.billing import Payment, Plan, Subscription
from app.models.catalog import Country, Episode, Genre, Season, Title, title_countries, title_genres
from app.models.enums import (
    NotificationType,
    PaymentScenario,
    PaymentStatus,
    SubscriptionStatus,
    TitleType,
    UserRole,
)
from app.models.media import Ad, VideoAsset
from app.models.user import User

__all__ = [
    "Ad",
    "Base",
    "Country",
    "Episode",
    "Favorite",
    "Genre",
    "Notification",
    "NotificationType",
    "Payment",
    "PaymentScenario",
    "PaymentStatus",
    "Plan",
    "Season",
    "Subscription",
    "SubscriptionStatus",
    "Title",
    "TitleType",
    "User",
    "UserRole",
    "VideoAsset",
    "WatchHistory",
    "title_countries",
    "title_genres",
]
