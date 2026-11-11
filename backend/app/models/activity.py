"""User activity: watch history, favorites, notifications."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, enum_column
from app.models.catalog import Title
from app.models.enums import NotificationType
from app.models.media import VideoAsset


class WatchHistory(Base):
    __tablename__ = "watch_history"
    __table_args__ = (UniqueConstraint("user_id", "video_asset_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    video_asset_id: Mapped[int] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True
    )
    progress_sec: Mapped[int] = mapped_column(default=0)
    completed: Mapped[bool] = mapped_column(default=False)
    last_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    video_asset: Mapped[VideoAsset] = relationship()


class Favorite(CreatedAtMixin, Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    title_id: Mapped[int] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True
    )

    title: Mapped[Title] = relationship()


class Notification(CreatedAtMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        enum_column(NotificationType, "notification_type")
    )
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False)
