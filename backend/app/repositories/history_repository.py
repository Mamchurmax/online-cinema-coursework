"""Data access for watch history."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Episode, Season, VideoAsset, WatchHistory


class WatchHistoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int, video_asset_id: int) -> WatchHistory | None:
        statement = select(WatchHistory).where(
            WatchHistory.user_id == user_id, WatchHistory.video_asset_id == video_asset_id
        )
        return self._db.scalars(statement).one_or_none()

    def list_recent(
        self, user_id: int, limit: int, *, unfinished_only: bool = False, min_progress_sec: int = 0
    ) -> Sequence[WatchHistory]:
        """Latest entries first, with the video, its title or episode (and season) loaded."""
        statement = (
            select(WatchHistory)
            .where(WatchHistory.user_id == user_id)
            .options(
                joinedload(WatchHistory.video_asset).joinedload(VideoAsset.title),
                joinedload(WatchHistory.video_asset)
                .joinedload(VideoAsset.episode)
                .joinedload(Episode.season)
                .joinedload(Season.title),
            )
            .order_by(WatchHistory.last_watched_at.desc(), WatchHistory.id.desc())
            .limit(limit)
        )
        if unfinished_only:
            statement = statement.where(
                WatchHistory.completed.is_(False), WatchHistory.progress_sec >= min_progress_sec
            )
        return self._db.scalars(statement).all()

    def save(self, entry: WatchHistory) -> WatchHistory:
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)
        return entry

    def delete(self, entry: WatchHistory) -> None:
        self._db.delete(entry)
        self._db.commit()
