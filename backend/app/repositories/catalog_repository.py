"""Data access for catalog entities: titles, genres, countries."""

from collections.abc import Sequence

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Country, Episode, Genre, Season, Title


class TitleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, title_id: int) -> Title | None:
        return self._db.get(Title, title_id)

    def get_by_tmdb_id(self, tmdb_id: int) -> Title | None:
        return self._db.scalars(select(Title).where(Title.tmdb_id == tmdb_id)).one_or_none()

    def get_with_details(self, title_id: int) -> Title | None:
        """Title with genres, countries, seasons and episodes loaded in a few queries."""
        statement = (
            select(Title)
            .where(Title.id == title_id)
            .options(
                selectinload(Title.genres),
                selectinload(Title.countries),
                selectinload(Title.video),
                selectinload(Title.seasons)
                .selectinload(Season.episodes)
                .selectinload(Episode.video),
            )
        )
        return self._db.scalars(statement).one_or_none()

    def find_page(
        self, statement: Select[tuple[Title]], count_statement: Select[tuple[int]]
    ) -> tuple[Sequence[Title], int]:
        """Run a prepared search (see `CatalogQueryBuilder`): one page and the total."""
        return self._db.scalars(statement).all(), self._db.scalar(count_statement) or 0

    def increment_watch_count(self, title_id: int) -> None:
        """Atomic `watch_count + 1`, safe when several viewers finish at once."""
        self._db.execute(
            update(Title).where(Title.id == title_id).values(watch_count=Title.watch_count + 1)
        )

    def add(self, title: Title) -> None:
        self._db.add(title)

    def delete(self, title: Title) -> None:
        self._db.delete(title)
        self._db.commit()

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

    def list_all(self) -> Sequence[Genre]:
        return self._db.scalars(select(Genre).order_by(Genre.name)).all()

    def get_many(self, ids: list[int]) -> Sequence[Genre]:
        return self._db.scalars(select(Genre).where(Genre.id.in_(ids))).all() if ids else []

    def add(self, genre: Genre) -> None:
        self._db.add(genre)
        self._db.flush()


class CountryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_code(self, code: str) -> Country | None:
        return self._db.scalars(select(Country).where(Country.code == code)).one_or_none()

    def list_all(self) -> Sequence[Country]:
        return self._db.scalars(select(Country).order_by(Country.name)).all()

    def get_many(self, codes: list[str]) -> Sequence[Country]:
        if not codes:
            return []
        return self._db.scalars(select(Country).where(Country.code.in_(codes))).all()

    def add(self, country: Country) -> None:
        self._db.add(country)
        self._db.flush()
