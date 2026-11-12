from datetime import datetime

from pydantic import BaseModel, Field

from app.models import TitleType, WatchHistory


class ProgressUpdate(BaseModel):
    position_sec: int = Field(ge=0, le=24 * 3600)


class HistoryEpisode(BaseModel):
    id: int
    season_number: int
    number: int
    name: str


class HistoryEntry(BaseModel):
    video_asset_id: int
    title_id: int
    title: str
    type: TitleType
    poster_url: str | None
    backdrop_url: str | None
    episode: HistoryEpisode | None
    progress_sec: int
    duration_sec: int
    completed: bool
    last_watched_at: datetime

    @classmethod
    def from_entry(cls, entry: WatchHistory) -> "HistoryEntry":
        video = entry.video_asset
        episode = video.episode
        title = video.title if episode is None else episode.season.title
        return cls(
            video_asset_id=video.id,
            title_id=title.id,
            title=title.title,
            type=title.type,
            poster_url=title.poster_url,
            backdrop_url=title.backdrop_url,
            episode=None
            if episode is None
            else HistoryEpisode(
                id=episode.id,
                season_number=episode.season.number,
                number=episode.number,
                name=episode.name,
            ),
            progress_sec=entry.progress_sec,
            duration_sec=video.duration_sec,
            completed=entry.completed,
            last_watched_at=entry.last_watched_at,
        )
