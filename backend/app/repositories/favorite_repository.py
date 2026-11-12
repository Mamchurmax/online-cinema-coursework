"""Data access for the user's favorites."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Favorite, Title


class FavoriteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int, title_id: int) -> Favorite | None:
        return self._db.get(Favorite, (user_id, title_id))

    def list_titles(self, user_id: int) -> Sequence[Title]:
        """Favorite titles, most recently added first."""
        statement = (
            select(Title)
            .join(Favorite, Favorite.title_id == Title.id)
            .where(Favorite.user_id == user_id)
            .options(selectinload(Title.genres), selectinload(Title.video))
            .order_by(Favorite.created_at.desc(), Title.id.desc())
        )
        return self._db.scalars(statement).all()

    def list_title_ids(self, user_id: int) -> Sequence[int]:
        return self._db.scalars(select(Favorite.title_id).where(Favorite.user_id == user_id)).all()

    def add(self, favorite: Favorite) -> None:
        self._db.add(favorite)
        self._db.commit()

    def delete(self, favorite: Favorite) -> None:
        self._db.delete(favorite)
        self._db.commit()
