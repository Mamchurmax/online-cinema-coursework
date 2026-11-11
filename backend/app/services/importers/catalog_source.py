"""Target interface of the catalog importer and the domain data it works with.

The import service depends only on `CatalogSource` and these dataclasses,
never on the format of a particular external API (see `TmdbAdapter`).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from app.models.enums import TitleType


@dataclass(frozen=True)
class GenreData:
    external_id: int
    name: str


@dataclass(frozen=True)
class CountryData:
    code: str  # ISO 3166-1 alpha-2
    name: str


@dataclass(frozen=True)
class EpisodeData:
    number: int
    name: str
    description: str
    duration: int | None  # minutes


@dataclass(frozen=True)
class SeasonData:
    number: int
    name: str
    episodes: list[EpisodeData] = field(default_factory=list)


@dataclass(frozen=True)
class TitleData:
    external_id: int
    type: TitleType
    title: str
    description: str
    release_year: int | None
    rating: Decimal | None
    poster_url: str | None
    backdrop_url: str | None
    duration: int | None  # minutes
    genres: list[GenreData] = field(default_factory=list)
    countries: list[CountryData] = field(default_factory=list)
    seasons: list[SeasonData] = field(default_factory=list)


class CatalogSource(Protocol):
    """Anything that can supply catalog metadata in domain form."""

    def get_movie(self, external_id: int) -> TitleData: ...

    def get_series(self, external_id: int, max_seasons: int | None = None) -> TitleData: ...

    def get_popular_ids(self, title_type: TitleType, pages: int = 1) -> list[int]: ...

    def get_anime_ids(self, title_type: TitleType, pages: int = 1) -> list[int]: ...
