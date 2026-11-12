"""Admin: create, edit and delete titles, seasons and episodes; import from TMDB."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.models import Episode, Season, Title, TitleType
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.repositories.content_repository import ContentRepository
from app.services.admin.errors import (
    AdminConflictError,
    AdminNotFoundError,
    AdminUnavailableError,
)
from app.services.importers.import_service import CatalogImportService


@dataclass(frozen=True)
class TitleFields:
    type: TitleType
    title: str
    description: str
    release_year: int | None
    rating: Decimal | None
    poster_url: str | None
    backdrop_url: str | None
    duration: int | None
    genre_ids: list[int]
    country_codes: list[str]


class CatalogAdminService:
    def __init__(
        self,
        titles: TitleRepository,
        genres: GenreRepository,
        countries: CountryRepository,
        content: ContentRepository,
        importer_factory: Callable[[], CatalogImportService] | None = None,
    ) -> None:
        self._titles = titles
        self._genres = genres
        self._countries = countries
        self._content = content
        # Built lazily: TMDB is only needed for imports and may be unconfigured.
        self._importer_factory = importer_factory

    # --- titles ------------------------------------------------------------------

    def create_title(self, fields: TitleFields) -> Title:
        title = Title()
        self._fill(title, fields)
        self._titles.add(title)
        self._titles.commit()
        return self._details(title.id)

    def update_title(self, title_id: int, fields: TitleFields) -> Title:
        title = self._require_title(title_id)
        if fields.type is not title.type and (title.seasons or title.video):
            raise AdminConflictError("Remove seasons or the video before changing the type")
        self._fill(title, fields)
        self._titles.commit()
        return self._details(title.id)

    def delete_title(self, title_id: int) -> None:
        """Seasons, episodes, videos, favorites and history entries go with it (cascade)."""
        self._titles.delete(self._require_title(title_id))

    def import_from_tmdb(self, tmdb_id: int, title_type: TitleType, max_seasons: int) -> Title:
        if self._importer_factory is None:
            raise AdminUnavailableError("TMDB_API_TOKEN is not configured")
        importer = self._importer_factory()
        if title_type is TitleType.MOVIE:
            report = importer.import_movies([tmdb_id])
        else:
            report = importer.import_series([tmdb_id], max_seasons)
        if report.failed:
            raise AdminNotFoundError(report.failed[0])
        if report.skipped:
            raise AdminConflictError(f"Skipped by catalog rules: {report.skipped[0]}")
        title = self._titles.get_by_tmdb_id(tmdb_id)
        assert title is not None
        return self._details(title.id)

    # --- seasons and episodes ---------------------------------------------------

    def add_season(self, title_id: int, number: int, name: str) -> Season:
        title = self._require_title(title_id)
        if title.type is not TitleType.SERIES:
            raise AdminConflictError("Only series have seasons")
        return self._save(Season(title_id=title.id, number=number, name=name), "season")

    def update_season(self, season_id: int, number: int, name: str) -> Season:
        season = self._content.get_season(season_id) or _missing("Season", season_id)
        season.number, season.name = number, name
        return self._save(season, "season")

    def delete_season(self, season_id: int) -> None:
        self._content.delete(self._content.get_season(season_id) or _missing("Season", season_id))

    def add_episode(self, season_id: int, fields: dict) -> Episode:
        season = self._content.get_season(season_id) or _missing("Season", season_id)
        return self._save(Episode(season_id=season.id, **fields), "episode")

    def update_episode(self, episode_id: int, fields: dict) -> Episode:
        episode = self._content.get_episode(episode_id) or _missing("Episode", episode_id)
        for key, value in fields.items():
            setattr(episode, key, value)
        return self._save(episode, "episode")

    def delete_episode(self, episode_id: int) -> None:
        episode = self._content.get_episode(episode_id) or _missing("Episode", episode_id)
        self._content.delete(episode)

    # --- internals ------------------------------------------------------------------

    def _fill(self, title: Title, fields: TitleFields) -> None:
        genres = self._genres.get_many(fields.genre_ids)
        if len(genres) != len(set(fields.genre_ids)):
            raise AdminNotFoundError("Unknown genre id")
        codes = [c.upper() for c in fields.country_codes]
        countries = self._countries.get_many(codes)
        if len(countries) != len(set(codes)):
            raise AdminNotFoundError("Unknown country code")

        title.type = fields.type
        title.title = fields.title.strip()
        title.description = fields.description.strip()
        title.release_year = fields.release_year
        title.rating = fields.rating
        title.poster_url = fields.poster_url or None
        title.backdrop_url = fields.backdrop_url or None
        title.duration = fields.duration
        title.genres = list(genres)
        title.countries = list(countries)

    def _save(self, item, what: str):  # noqa: ANN001, ANN202
        try:
            self._content.save(item)
        except IntegrityError:
            self._content.rollback()
            raise AdminConflictError(f"A {what} with this number already exists") from None
        return item

    def _require_title(self, title_id: int) -> Title:
        return self._titles.get(title_id) or _missing("Title", title_id)

    def _details(self, title_id: int) -> Title:
        title = self._titles.get_with_details(title_id)
        assert title is not None
        return title


def _missing(what: str, object_id: int):  # noqa: ANN202
    raise AdminNotFoundError(f"{what} {object_id} not found")
