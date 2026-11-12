"""Data access for seasons and episodes (used by the admin panel)."""

from sqlalchemy.orm import Session

from app.models import Episode, Season


class ContentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_season(self, season_id: int) -> Season | None:
        return self._db.get(Season, season_id)

    def get_episode(self, episode_id: int) -> Episode | None:
        return self._db.get(Episode, episode_id)

    def save(self, item: Season | Episode) -> None:
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)

    def delete(self, item: Season | Episode) -> None:
        self._db.delete(item)
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
