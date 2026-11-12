"""Read-only queries for the admin reports.

Each method returns flat rows for a half-open time range [start, end); grouping by
day, plan or genre happens in the reports themselves (the `aggregate` step).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Episode,
    Genre,
    Payment,
    PaymentStatus,
    Plan,
    Season,
    Subscription,
    SubscriptionStatus,
    Title,
    TitleType,
    User,
    VideoAsset,
    WatchHistory,
    title_genres,
)


@dataclass(frozen=True)
class WatchRow:
    """One watch_history record: a user's last position in one video."""

    user_id: int
    title_id: int  # an episode counts as its series
    progress_sec: int
    completed: bool
    watched_at: datetime
    duration_sec: int

    @property
    def watched_sec(self) -> int:
        """A finished video counts in full: after "watch again" the position starts over."""
        if self.completed:
            return self.duration_sec
        return min(self.progress_sec, self.duration_sec)


@dataclass(frozen=True)
class TitleInfo:
    id: int
    title: str
    type: TitleType


@dataclass(frozen=True)
class UserInfo:
    id: int
    email: str
    display_name: str


@dataclass(frozen=True)
class PaymentRow:
    user_id: int
    plan_code: str
    plan_name: str
    amount: Decimal
    status: PaymentStatus
    created_at: datetime


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # --- viewing ---------------------------------------------------------------------

    def watch_rows(self, start: datetime, end: datetime) -> list[WatchRow]:
        title_of_video = func.coalesce(VideoAsset.title_id, Season.title_id)
        rows = self._db.execute(
            select(
                WatchHistory.user_id,
                title_of_video,
                WatchHistory.progress_sec,
                WatchHistory.completed,
                WatchHistory.last_watched_at,
                VideoAsset.duration_sec,
            )
            .select_from(WatchHistory)
            .join(VideoAsset, VideoAsset.id == WatchHistory.video_asset_id)
            .outerjoin(Episode, Episode.id == VideoAsset.episode_id)
            .outerjoin(Season, Season.id == Episode.season_id)
            .where(WatchHistory.last_watched_at >= start, WatchHistory.last_watched_at < end)
        ).all()
        return [WatchRow(*row) for row in rows]

    def titles(self, title_ids: set[int]) -> dict[int, TitleInfo]:
        if not title_ids:
            return {}
        rows = self._db.execute(
            select(Title.id, Title.title, Title.type).where(Title.id.in_(title_ids))
        ).all()
        return {row[0]: TitleInfo(*row) for row in rows}

    def genres_of(self, title_ids: set[int]) -> dict[int, list[str]]:
        """title id -> names of its genres."""
        if not title_ids:
            return {}
        rows = self._db.execute(
            select(title_genres.c.title_id, Genre.name)
            .join(Genre, Genre.id == title_genres.c.genre_id)
            .where(title_genres.c.title_id.in_(title_ids))
        ).all()
        result: dict[int, list[str]] = {}
        for title_id, name in rows:
            result.setdefault(title_id, []).append(name)
        return result

    # --- users -----------------------------------------------------------------------

    def count_users(self, before: datetime) -> int:
        return self._db.scalar(select(func.count(User.id)).where(User.created_at < before)) or 0

    def registrations(self, start: datetime, end: datetime) -> Sequence[datetime]:
        return self._db.scalars(
            select(User.created_at).where(User.created_at >= start, User.created_at < end)
        ).all()

    def users(self, user_ids: set[int]) -> dict[int, UserInfo]:
        if not user_ids:
            return {}
        rows = self._db.execute(
            select(User.id, User.email, User.display_name).where(User.id.in_(user_ids))
        ).all()
        return {row[0]: UserInfo(*row) for row in rows}

    # --- money -----------------------------------------------------------------------

    def payments(self, start: datetime, end: datetime) -> list[PaymentRow]:
        rows = self._db.execute(
            select(
                Payment.user_id, Plan.code, Plan.name, Payment.amount, Payment.status,
                Payment.created_at,
            )  # fmt: skip
            .join(Plan, Plan.id == Payment.plan_id)
            .where(Payment.created_at >= start, Payment.created_at < end)
            .order_by(Payment.created_at)
        ).all()
        return [PaymentRow(*row) for row in rows]

    def active_subscriptions_by_plan(self, at: datetime) -> dict[str, int]:
        """Plan name -> subscriptions active at the given moment."""
        rows = self._db.execute(
            select(Plan.name, func.count(Subscription.id))
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.started_at <= at,
                Subscription.expires_at > at,
            )
            .group_by(Plan.name)
        ).all()
        return dict(rows)
