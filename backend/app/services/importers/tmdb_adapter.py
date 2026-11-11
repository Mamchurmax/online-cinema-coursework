"""Pattern: Adapter (GoF).

- Target:  `CatalogSource` — the interface the import service expects.
- Adaptee: `TmdbClient` — returns raw TMDB JSON with its own field names
  (`overview`, `vote_average`, `first_air_date`, `iso_3166_1`, image paths, ...).
- Adapter: `TmdbAdapter` — implements `CatalogSource` by calling `TmdbClient`
  and converting its responses into domain dataclasses (`TitleData`, ...).

Thanks to the adapter, the rest of the system knows nothing about TMDB; another
metadata provider can be added by writing one more adapter.
"""

import logging
from collections.abc import Callable
from decimal import Decimal

from app.models.enums import TitleType
from app.services.importers.catalog_source import (
    CatalogSource,
    CountryData,
    EpisodeData,
    GenreData,
    SeasonData,
    TitleData,
)
from app.services.importers.tmdb_client import Json, TmdbClient, TmdbError

logger = logging.getLogger(__name__)

IMAGE_BASE_URL = "https://image.tmdb.org/t/p"
POSTER_SIZE = "w500"
BACKDROP_SIZE = "w1280"

PRIMARY_LANGUAGE = "uk-UA"
FALLBACK_LANGUAGE = "en-US"

_MEDIA_BY_TYPE = {TitleType.MOVIE: "movie", TitleType.SERIES: "tv"}


class TmdbAdapter(CatalogSource):
    """Adapter: exposes `TmdbClient` through the `CatalogSource` interface."""

    def __init__(self, client: TmdbClient) -> None:
        self._client = client
        self._country_names: dict[str, str] | None = None  # ISO code -> localized name

    def get_movie(self, external_id: int) -> TitleData:
        raw = self._client.movie(external_id, PRIMARY_LANGUAGE)
        fallback = self._fallback_if_untranslated(
            raw, lambda: self._client.movie(external_id, FALLBACK_LANGUAGE)
        )

        return TitleData(
            external_id=raw["id"],
            type=TitleType.MOVIE,
            title=self._text(raw, fallback, "title"),
            description=self._text(raw, fallback, "overview"),
            release_year=self._year(raw.get("release_date")),
            rating=self._rating(raw.get("vote_average")),
            poster_url=self._image(raw.get("poster_path"), POSTER_SIZE),
            backdrop_url=self._image(raw.get("backdrop_path"), BACKDROP_SIZE),
            duration=raw.get("runtime") or None,
            genres=self._genres(raw),
            countries=self._countries(raw),
        )

    def get_series(self, external_id: int, max_seasons: int | None = None) -> TitleData:
        raw = self._client.tv(external_id, PRIMARY_LANGUAGE)
        fallback = self._fallback_if_untranslated(
            raw, lambda: self._client.tv(external_id, FALLBACK_LANGUAGE)
        )

        season_numbers = sorted(
            s["season_number"] for s in raw.get("seasons", []) if s.get("season_number", 0) > 0
        )  # season 0 holds "specials" and is skipped
        if max_seasons is not None:
            season_numbers = season_numbers[:max_seasons]

        run_times = raw.get("episode_run_time") or []
        return TitleData(
            external_id=raw["id"],
            type=TitleType.SERIES,
            title=self._text(raw, fallback, "name"),
            description=self._text(raw, fallback, "overview"),
            release_year=self._year(raw.get("first_air_date")),
            rating=self._rating(raw.get("vote_average")),
            poster_url=self._image(raw.get("poster_path"), POSTER_SIZE),
            backdrop_url=self._image(raw.get("backdrop_path"), BACKDROP_SIZE),
            duration=run_times[0] if run_times else None,
            genres=self._genres(raw),
            countries=self._countries(raw),
            seasons=[self._season(external_id, number) for number in season_numbers],
        )

    def get_popular_ids(self, title_type: TitleType, pages: int = 1) -> list[int]:
        media = _MEDIA_BY_TYPE[title_type]
        ids: list[int] = []
        for page in range(1, pages + 1):
            results = self._client.popular(media, page, PRIMARY_LANGUAGE)["results"]
            ids.extend(item["id"] for item in results)
        return ids

    # --- conversion helpers -------------------------------------------------

    def _season(self, tv_id: int, number: int) -> SeasonData:
        raw = self._client.tv_season(tv_id, number, PRIMARY_LANGUAGE)
        return SeasonData(
            number=number,
            name=raw.get("name") or f"Сезон {number}",
            episodes=[
                EpisodeData(
                    number=ep["episode_number"],
                    name=ep.get("name") or f"Епізод {ep['episode_number']}",
                    description=ep.get("overview") or "",
                    duration=ep.get("runtime") or None,
                )
                for ep in raw.get("episodes", [])
            ],
        )

    @staticmethod
    def _fallback_if_untranslated(raw: Json, load_fallback: Callable[[], Json]) -> Json | None:
        """TMDB returns an empty overview when there is no Ukrainian translation."""
        return None if raw.get("overview") else load_fallback()

    @staticmethod
    def _text(raw: Json, fallback: Json | None, key: str) -> str:
        value = raw.get(key) or ""
        if not value and fallback is not None:
            value = fallback.get(key) or ""
        return value.strip()

    @staticmethod
    def _year(date: str | None) -> int | None:
        return int(date[:4]) if date and len(date) >= 4 else None

    @staticmethod
    def _rating(vote_average: float | None) -> Decimal | None:
        if not vote_average:
            return None
        return Decimal(str(vote_average)).quantize(Decimal("0.1"))

    @staticmethod
    def _image(path: str | None, size: str) -> str | None:
        return f"{IMAGE_BASE_URL}/{size}{path}" if path else None

    @staticmethod
    def _genres(raw: Json) -> list[GenreData]:
        return [GenreData(external_id=g["id"], name=g["name"]) for g in raw.get("genres", [])]

    def _countries(self, raw: Json) -> list[CountryData]:
        """Production and origin countries, named in the primary language when possible."""
        names = {c["iso_3166_1"]: c["name"] for c in raw.get("production_countries", [])}
        for code in raw.get("origin_country", []):  # TMDB gives only codes here
            names.setdefault(code, code)

        localized = self._localized_country_names()
        return [
            CountryData(code=code, name=localized.get(code) or name)
            for code, name in names.items()
        ]

    def _localized_country_names(self) -> dict[str, str]:
        """Loaded once per adapter: titles only carry English country names."""
        if self._country_names is None:
            try:
                countries = self._client.countries(PRIMARY_LANGUAGE)
                self._country_names = {
                    c["iso_3166_1"]: c.get("native_name") or c["english_name"] for c in countries
                }
            except TmdbError as exc:  # names stay in English; the import itself goes on
                logger.warning("Localized country names are unavailable: %s", exc)
                self._country_names = {}
        return self._country_names
