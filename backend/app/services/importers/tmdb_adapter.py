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
import re
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

TMDB_ANIMATION_GENRE_ID = 16
# TV genres that do not belong in a cinema catalog: News, Reality, Soap, Talk.
TMDB_NON_CINEMA_GENRE_IDS = frozenset({10763, 10764, 10766, 10767})

_MEDIA_BY_TYPE = {TitleType.MOVIE: "movie", TitleType.SERIES: "tv"}

# TMDB fills untranslated episode names with "Серія 5" / "Episode 5".
_PLACEHOLDER_EPISODE_NAME = re.compile(r"^(Серія|Епізод|Episode)\s+\d+$", re.IGNORECASE)


class TmdbAdapter(CatalogSource):
    """Adapter: exposes `TmdbClient` through the `CatalogSource` interface."""

    def __init__(self, client: TmdbClient) -> None:
        self._client = client
        self._country_names: dict[str, str] | None = None  # ISO code -> localized name

    def get_movie(self, external_id: int) -> TitleData:
        raw = self._client.movie(external_id, PRIMARY_LANGUAGE)
        title, description = self._localized_texts(raw, "title")

        return TitleData(
            external_id=raw["id"],
            type=TitleType.MOVIE,
            title=title,
            description=description,
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
        title, description = self._localized_texts(raw, "name")

        season_numbers = sorted(
            s["season_number"] for s in raw.get("seasons", []) if s.get("season_number", 0) > 0
        )  # season 0 holds "specials" and is skipped
        if max_seasons is not None:
            season_numbers = season_numbers[:max_seasons]

        run_times = raw.get("episode_run_time") or []
        return TitleData(
            external_id=raw["id"],
            type=TitleType.SERIES,
            title=title,
            description=description,
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
        return _collect_ids(lambda page: self._client.popular(media, page, PRIMARY_LANGUAGE), pages)

    def get_anime_ids(self, title_type: TitleType, pages: int = 1) -> list[int]:
        """Most popular Japanese animation."""
        media = _MEDIA_BY_TYPE[title_type]
        return _collect_ids(
            lambda page: self._client.discover(
                media,
                page,
                PRIMARY_LANGUAGE,
                with_genres=TMDB_ANIMATION_GENRE_ID,
                with_original_language="ja",
            ),
            pages,
        )

    # --- conversion helpers -------------------------------------------------

    @staticmethod
    def _localized_texts(raw: Json, title_key: str) -> tuple[str, str]:
        """Title and description: Ukrainian if translated, otherwise English, otherwise original.

        Without a Ukrainian translation TMDB returns the *original* title (Japanese,
        Hindi, ...) and an empty overview, so the English translation is used instead.
        """
        translations = raw.get("translations", {}).get("translations", [])
        uk = _translation(translations, "uk")
        en = _translation(translations, "en", preferred_country="US")
        original_is_ukrainian = raw.get("original_language") == "uk"

        title = _first_text(
            [
                uk.get(title_key),
                raw.get(title_key) if original_is_ukrainian else None,
                en.get(title_key),
                raw.get(title_key),
            ]
        )
        description = _first_text([uk.get("overview"), raw.get("overview"), en.get("overview")])
        return title, description

    def _season(self, tv_id: int, number: int) -> SeasonData:
        raw = self._client.tv_season(tv_id, number, PRIMARY_LANGUAGE)
        episodes = raw.get("episodes", [])

        # Untranslated episodes come as "Серія 5" with no overview: load English once.
        english: dict[int, Json] = {}
        if any(_is_placeholder(ep.get("name")) or not ep.get("overview") for ep in episodes):
            english_raw = self._client.tv_season(tv_id, number, FALLBACK_LANGUAGE)
            english = {ep["episode_number"]: ep for ep in english_raw.get("episodes", [])}

        return SeasonData(
            number=number,
            name=raw.get("name") or f"Сезон {number}",
            episodes=[self._episode(ep, english.get(ep["episode_number"], {})) for ep in episodes],
        )

    @staticmethod
    def _episode(raw: Json, english: Json) -> EpisodeData:
        number = raw["episode_number"]
        name = raw.get("name")
        if _is_placeholder(name) and not _is_placeholder(english.get("name")):
            name = english["name"]
        return EpisodeData(
            number=number,
            name=_first_text([name]) or f"Епізод {number}",
            description=_first_text([raw.get("overview"), english.get("overview")]),
            duration=raw.get("runtime") or None,
        )

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


def _collect_ids(load_page: Callable[[int], Json], pages: int) -> list[int]:
    ids: list[int] = []
    for page in range(1, pages + 1):
        ids.extend(item["id"] for item in load_page(page)["results"])
    return ids


def _translation(translations: list[Json], language: str, preferred_country: str = "") -> Json:
    """`data` of the translation into `language` (e.g. "uk"), or an empty dict."""
    matching = [t for t in translations if t.get("iso_639_1") == language]
    matching.sort(key=lambda t: t.get("iso_3166_1") != preferred_country)
    return matching[0].get("data", {}) if matching else {}


def _first_text(candidates: list[str | None]) -> str:
    return next((c.strip() for c in candidates if c and c.strip()), "")


def _is_placeholder(name: str | None) -> bool:
    return not name or bool(_PLACEHOLDER_EPISODE_NAME.match(name.strip()))
