"""Watch history: progress of each video, resume position, "continue watching"."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from app.models import User, WatchHistory
from app.repositories.history_repository import WatchHistoryRepository
from app.repositories.media_repository import VideoAssetRepository

# A video counts as watched once 90% of it is behind (end credits are usually skipped).
COMPLETED_SHARE = 0.9
# "Continue watching" ignores videos that were only opened for a few seconds.
MIN_RESUME_SEC = 10


class VideoNotFoundError(Exception):
    pass


class HistoryEntryNotFoundError(Exception):
    pass


class WatchHistoryService:
    def __init__(
        self,
        history: WatchHistoryRepository,
        videos: VideoAssetRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._history = history
        self._videos = videos
        self._clock = clock

    def save_progress(self, user: User, video_asset_id: int, position_sec: int) -> WatchHistory:
        """Remember where the viewer is. Called by the player every few seconds."""
        video = self._videos.get(video_asset_id)
        if video is None:
            raise VideoNotFoundError(video_asset_id)

        position = max(0, min(position_sec, video.duration_sec))
        entry = self._history.get(user.id, video_asset_id) or WatchHistory(
            user_id=user.id, video_asset_id=video_asset_id
        )
        entry.progress_sec = position
        # Once finished, a film stays "watched" even if it is opened again later.
        entry.completed = bool(entry.completed) or position >= video.duration_sec * COMPLETED_SHARE
        entry.last_watched_at = self._clock()
        return self._history.save(entry)

    def resume_position(self, user: User, video_asset_id: int) -> int:
        """Where playback should start: the saved position, or 0 for new/finished videos."""
        entry = self._history.get(user.id, video_asset_id)
        if entry is None or entry.progress_sec < MIN_RESUME_SEC:
            return 0
        video = self._videos.get(video_asset_id)
        if video is not None and entry.progress_sec >= video.duration_sec * COMPLETED_SHARE:
            return 0  # finished: start again from the beginning
        return entry.progress_sec

    def continue_watching(self, user: User, limit: int = 12) -> Sequence[WatchHistory]:
        return self._history.list_recent(
            user.id, limit, unfinished_only=True, min_progress_sec=MIN_RESUME_SEC
        )

    def history(self, user: User, limit: int = 100) -> Sequence[WatchHistory]:
        return self._history.list_recent(user.id, limit)

    def remove(self, user: User, video_asset_id: int) -> None:
        entry = self._history.get(user.id, video_asset_id)
        if entry is None:
            raise HistoryEntryNotFoundError(video_asset_id)
        self._history.delete(entry)
