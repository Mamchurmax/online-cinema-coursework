"""Data access for catalog entities: titles, genres, countries."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Genre, Title


class TitleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, title_id: int) -> Title | None:
        return self._db.get(Title, title_id)

    def get_by_tmdb_id(self, tmdb_id: int) -> Title | None:
        return self._db.scalars(select(Title).where(Title.tmdb_id == tmdb_id)).one_or_none()

    def add(self, title: Title) -> None:
        self._db.add(title)

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()


class GenreRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_tmdb_id(self, tmdb_id: int) -> Genre | None:
        return self._db.scalars(select(Genre).where(Genre.tmdb_id == tmdb_id)).one_or_none()

    def get_by_name(self, name: str) -> Genre | None:
        return self._db.scalars(select(Genre).where(Genre.name == name)).one_or_none()

    def add(self, genre: Genre) -> None:
        self._db.add(genre)
        self._db.flush()


class CountryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_code(self, code: str) -> Country | None:
        return self._db.scalars(select(Country).where(Country.code == code)).one_or_none()

    def add(self, country: Country) -> None:
        self._db.add(country)
        self._db.flush()
