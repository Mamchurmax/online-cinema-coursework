"""Read-only queries used by the recommendation strategies."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Episode,
    Favorite,
    Genre,
    Season,
    Title,
    VideoAsset,
    WatchHistory,
    title_genres,
)


@dataclass(frozen=True)
class ViewingSignal:
    """One thing the user did with a title: watched (partly or fully) or saved it."""

    title_id: int
    completed: bool = False
    favorite: bool = False


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def viewing_signals(self, user_id: int) -> list[ViewingSignal]:
        """Watched titles (an episode counts as its series) and favorites of the user."""
        title_of_video = func.coalesce(VideoAsset.title_id, Season.title_id)
        watched = self._db.execute(
            select(title_of_video, func.max(cast(WatchHistory.completed, Integer)))
            .select_from(WatchHistory)
            .join(VideoAsset, VideoAsset.id == WatchHistory.video_asset_id)
            .outerjoin(Episode, Episode.id == VideoAsset.episode_id)
            .outerjoin(Season, Season.id == Episode.season_id)
            .where(WatchHistory.user_id == user_id)
            .group_by(title_of_video)
        ).all()
        favorites = self._db.scalars(select(Favorite.title_id).where(Favorite.user_id == user_id))
        return [ViewingSignal(title_id, completed=bool(done)) for title_id, done in watched] + [
            ViewingSignal(title_id, favorite=True) for title_id in favorites
        ]

    def genres_of(self, title_ids: set[int]) -> dict[int, list[int]]:
        """title id -> its genre ids."""
        if not title_ids:
            return {}
        rows = self._db.execute(
            select(title_genres.c.title_id, title_genres.c.genre_id).where(
                title_genres.c.title_id.in_(title_ids)
            )
        ).all()
        result: dict[int, list[int]] = {}
        for title_id, genre_id in rows:
            result.setdefault(title_id, []).append(genre_id)
        return result

    def titles_with_genres(
        self, genre_ids: set[int], exclude: set[int], limit: int
    ) -> Sequence[Title]:
        """Candidates sharing at least one genre; best rated first, so the pool is useful."""
        if not genre_ids:
            return []
        statement = (
            select(Title)
            .where(Title.genres.any(Genre.id.in_(genre_ids)))
            .options(selectinload(Title.genres), selectinload(Title.video))
            .order_by(Title.rating.desc().nulls_last(), Title.id)
            .limit(limit)
        )
        if exclude:
            statement = statement.where(Title.id.not_in(exclude))
        return self._db.scalars(statement).all()

    def popular_titles(self, exclude: set[int], limit: int) -> Sequence[Title]:
        """Most watched to the end on the site, then best rated."""
        statement = (
            select(Title)
            .options(selectinload(Title.genres), selectinload(Title.video))
            .order_by(Title.watch_count.desc(), Title.rating.desc().nulls_last(), Title.id)
            .limit(limit)
        )
        if exclude:
            statement = statement.where(Title.id.not_in(exclude))
        return self._db.scalars(statement).all()

    def genre_names(self, genre_ids: set[int]) -> dict[int, str]:
        if not genre_ids:
            return {}
        rows = self._db.execute(select(Genre.id, Genre.name).where(Genre.id.in_(genre_ids)))
        return dict(rows.all())
