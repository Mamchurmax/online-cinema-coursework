"""Imports catalog metadata from any `CatalogSource` into the database."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from app.models import Country, Episode, Genre, Season, Title, TitleType
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.services.importers.catalog_source import (
    CatalogSource,
    CountryData,
    GenreData,
    TitleData,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class CatalogImportService:
    """Creates or updates titles by their external (TMDB) id, so re-import is safe."""

    def __init__(
        self,
        source: CatalogSource,
        titles: TitleRepository,
        genres: GenreRepository,
        countries: CountryRepository,
    ) -> None:
        self._source = source
        self._titles = titles
        self._genres = genres
        self._countries = countries

    def import_movies(
        self, external_ids: list[int], report: ImportReport | None = None
    ) -> ImportReport:
        report = report or ImportReport()
        for external_id in external_ids:
            self._import_one(
                lambda: self._source.get_movie(external_id), f"movie {external_id}", report
            )
        return report

    def import_series(
        self,
        external_ids: list[int],
        max_seasons: int | None = None,
        report: ImportReport | None = None,
    ) -> ImportReport:
        report = report or ImportReport()
        for external_id in external_ids:
            self._import_one(
                lambda: self._source.get_series(external_id, max_seasons),
                f"series {external_id}",
                report,
            )
        return report

    def import_popular(
        self,
        title_type: TitleType,
        pages: int,
        max_seasons: int | None = None,
        report: ImportReport | None = None,
    ) -> ImportReport:
        ids = self._source.get_popular_ids(title_type, pages)
        if title_type is TitleType.MOVIE:
            return self.import_movies(ids, report)
        return self.import_series(ids, max_seasons, report)

    # --- internals ------------------------------------------------------------

    def _import_one(
        self, fetch: Callable[[], TitleData], label: str, report: ImportReport
    ) -> None:
        try:
            data = fetch()
            created = self._upsert(data)
            self._titles.commit()
        except Exception as exc:  # one broken title must not stop a batch import
            self._titles.rollback()
            logger.warning("Import of %s failed: %s", label, exc)
            report.failed.append(f"{label}: {exc}")
            return

        bucket = report.created if created else report.updated
        bucket.append(f"{data.title} ({data.release_year})")

    def _upsert(self, data: TitleData) -> bool:
        """Copy `data` into a `Title`; return True if the title is new."""
        title = self._titles.get_by_tmdb_id(data.external_id)
        created = title is None
        if title is None:
            title = Title(tmdb_id=data.external_id)
            self._titles.add(title)

        title.type = data.type
        title.title = data.title
        title.description = data.description
        title.release_year = data.release_year
        title.rating = data.rating
        title.poster_url = data.poster_url
        title.backdrop_url = data.backdrop_url
        title.duration = data.duration
        title.genres = [self._genre(g) for g in data.genres]
        title.countries = [self._country(c) for c in data.countries]

        if data.type is TitleType.SERIES:
            self._sync_seasons(title, data)
        return created

    def _sync_seasons(self, title: Title, data: TitleData) -> None:
        """Update seasons/episodes in place, keeping rows that videos may already reference."""
        existing_seasons = {s.number: s for s in title.seasons}
        for season_data in data.seasons:
            season = existing_seasons.get(season_data.number)
            if season is None:
                season = Season(number=season_data.number, name=season_data.name)
                title.seasons.append(season)
            season.name = season_data.name

            existing_episodes = {e.number: e for e in season.episodes}
            for ep in season_data.episodes:
                episode = existing_episodes.get(ep.number)
                if episode is None:
                    episode = Episode(number=ep.number, name=ep.name)
                    season.episodes.append(episode)
                episode.name = ep.name
                episode.description = ep.description
                episode.duration = ep.duration

    def _genre(self, data: GenreData) -> Genre:
        genre = self._genres.get_by_tmdb_id(data.external_id) or self._genres.get_by_name(data.name)
        if genre is None:
            genre = Genre(tmdb_id=data.external_id, name=data.name)
            self._genres.add(genre)
        genre.tmdb_id = data.external_id
        return genre

    def _country(self, data: CountryData) -> Country:
        country = self._countries.get_by_code(data.code)
        if country is None:
            country = Country(code=data.code, name=data.name)
            self._countries.add(country)
        elif data.name != data.code:  # a real name beats a bare code
            country.name = data.name
        return country
