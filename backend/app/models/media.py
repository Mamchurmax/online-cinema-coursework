"""Video files (HLS) and pre-roll ads."""

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin
from app.models.catalog import Episode, Title


class VideoAsset(CreatedAtMixin, Base):
    """HLS video attached to exactly one movie title or one episode."""

    __tablename__ = "video_assets"
    __table_args__ = (
        CheckConstraint(
            "(title_id IS NULL) <> (episode_id IS NULL)", name="exactly_one_owner"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int | None] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), unique=True
    )
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), unique=True
    )
    hls_path: Mapped[str] = mapped_column(String(500))  # master playlist, relative to media/
    qualities: Mapped[list[str]] = mapped_column(JSON, default=list)  # e.g. ["360p", "720p"]
    duration_sec: Mapped[int]

    title: Mapped[Title | None] = relationship()
    episode: Mapped[Episode | None] = relationship()


class Ad(CreatedAtMixin, Base):
    """Pre-roll ad shown to Free plan users."""

    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    hls_path: Mapped[str] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(default=True)
