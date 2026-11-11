"""TMDB adapter and catalog import, with TMDB replaced by an in-process fake."""

from decimal import Decimal

import httpx2
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Country, Episode, Genre, Season, Title, TitleType
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.services.importers.import_service import CatalogImportService
from app.services.importers.tmdb_adapter import TMDB_NON_CINEMA_GENRE_IDS, TmdbAdapter
from app.services.importers.tmdb_client import TmdbClient, TmdbError


def translations(*items: tuple[str, str, dict]) -> dict:
    """TMDB `append_to_response=translations` block."""
    return {
        "translations": [
            {"iso_639_1": lang, "iso_3166_1": country, "data": data}
            for lang, country, data in items
        ]
    }


def episode(number: int, name: str, overview: str | None = None, runtime: int | None = None):
    return {"episode_number": number, "name": name, "overview": overview, "runtime": runtime}


MOVIE_UK = {
    "id": 603,
    "title": "Матриця",
    "original_language": "en",
    "overview": "Хакер Нео дізнається правду про реальність.",
    "release_date": "1999-03-31",
    "vote_average": 8.217,
    "poster_path": "/poster.jpg",
    "backdrop_path": "/backdrop.jpg",
    "runtime": 136,
    "genres": [{"id": 28, "name": "Бойовик"}, {"id": 878, "name": "Фантастика"}],
    "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
    "origin_country": ["US"],
    "translations": translations(
        ("uk", "UA", {"title": "Матриця", "overview": "Хакер Нео дізнається правду."}),
        ("en", "US", {"title": "The Matrix", "overview": "A hacker learns the truth."}),
    ),
}

# No Ukrainian translation: TMDB returns the original title and an empty overview.
UNTRANSLATED_MOVIE_UK = {
    "id": 10378,
    "title": "Big Buck Bunny",
    "original_language": "en",
    "overview": "",
    "release_date": "2008-05-30",
    "vote_average": 6.4,
    "poster_path": None,
    "backdrop_path": None,
    "runtime": 10,
    "genres": [{"id": 16, "name": "Мультфільм"}],
    "production_countries": [{"iso_3166_1": "NL", "name": "Netherlands"}],
    "translations": translations(
        ("en", "GB", {"title": "Big Buck Bunny (UK)", "overview": "British overview."}),
        ("en", "US", {"title": "Big Buck Bunny", "overview": "A giant rabbit."}),
    ),
}

UKRAINIAN_MOVIE_UK = {
    "id": 41116,
    "title": "Тіні забутих предків",
    "original_language": "uk",
    "overview": "Карпатська легенда.",
    "release_date": "1965-01-01",
    "vote_average": 7.6,
    "genres": [{"id": 18, "name": "Драма"}],
    "production_countries": [{"iso_3166_1": "UA", "name": "Ukraine"}],
    # The original language is not in the translations list.
    "translations": translations(("en", "US", {"title": "Shadows of Forgotten Ancestors"})),
}

SERIES_UK = {
    "id": 1399,
    "name": "Гра престолів",
    "original_language": "en",
    "overview": "Боротьба за Залізний трон.",
    "first_air_date": "2011-04-17",
    "vote_average": 8.46,
    "poster_path": "/got.jpg",
    "backdrop_path": None,
    "episode_run_time": [60],
    "genres": [{"id": 18, "name": "Драма"}],
    "production_countries": [],
    "origin_country": ["US"],
    "seasons": [
        {"season_number": 0, "name": "Спецвипуски"},
        {"season_number": 1, "name": "Сезон 1"},
        {"season_number": 2, "name": "Сезон 2"},
    ],
    "translations": translations(
        ("uk", "UA", {"name": "Гра престолів", "overview": "Боротьба за Залізний трон."}),
        ("en", "US", {"name": "Game of Thrones", "overview": "Seven noble families fight."}),
    ),
}

JAPANESE_SERIES_UK = {
    "id": 46052,
    "name": "ドクターX ～外科医・大門未知子～",
    "original_language": "ja",
    "overview": "",
    "first_air_date": "2012-10-18",
    "vote_average": 7.9,
    "genres": [{"id": 18, "name": "Драма"}],
    "origin_country": ["JP"],
    "seasons": [{"season_number": 1, "name": "Сезон 1"}],
    "translations": translations(
        ("ja", "JP", {"name": "ドクターX", "overview": "日本語の説明"}),
        ("en", "US", {"name": "Doctor-X: Surgeon Michiko Daimon", "overview": "A surgeon."}),
    ),
}

TALK_SHOW_UK = {
    "id": 2000,
    "name": "Вечірнє шоу",
    "overview": "Щовечора нові гості.",
    "genres": [{"id": 10767, "name": "Ток-шоу"}, {"id": 35, "name": "Комедія"}],
    "seasons": [{"season_number": 1}],
    "translations": translations(("uk", "UA", {"name": "Вечірнє шоу", "overview": "Гості."})),
}

LONG_SERIES_UK = {
    "id": 3000,
    "name": "Довгий серіал",
    "overview": "Дуже багато серій.",
    "genres": [{"id": 16, "name": "Мультфільм"}],
    "seasons": [{"season_number": 1}],
    "translations": translations(("uk", "UA", {"name": "Довгий серіал", "overview": "Багато."})),
}

SEASONS = {
    ("/tv/1399/season/1", "uk-UA"): {
        "name": "Сезон 1",
        "episodes": [episode(1, "Зима близько", "Пролог.", 62), episode(2, "")],
    },
    ("/tv/1399/season/1", "en-US"): {
        "episodes": [
            episode(1, "Winter Is Coming", "Prologue."),
            episode(2, "The Kingsroad", "The Starks travel south."),
        ],
    },
    ("/tv/1399/season/2", "uk-UA"): {
        "name": "Сезон 2",
        "episodes": [episode(1, "Північ пам'ятає", "Початок другого сезону.")],
    },
    ("/tv/46052/season/1", "uk-UA"): {
        "name": "Сезон 1",
        "episodes": [episode(1, "Серія 1"), episode(2, "Серія 2")],
    },
    ("/tv/46052/season/1", "en-US"): {
        "episodes": [episode(1, "OPE.1", "First operation."), episode(2, "Episode 2")],
    },
    ("/tv/2000/season/1", "uk-UA"): {"episodes": [episode(1, "Гість 1", "Опис.")]},
    ("/tv/3000/season/1", "uk-UA"): {
        "episodes": [episode(n, f"Пригода {n}", f"Опис {n}.") for n in range(1, 6)],
    },
}

POPULAR_MOVIES = {1: {"results": [{"id": 603}]}, 2: {"results": [{"id": 10378}]}}
ANIME = {"movie": {"results": [{"id": 10378}]}, "tv": {"results": [{"id": 46052}]}}

COUNTRIES_UK = [
    {"iso_3166_1": "US", "english_name": "United States of America", "native_name": "США"},
    {"iso_3166_1": "NL", "english_name": "Netherlands", "native_name": "Нідерланди"},
    {"iso_3166_1": "JP", "english_name": "Japan", "native_name": "Японія"},
]


class FakeTmdb:
    """Serves canned TMDB responses and records every request."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.overrides: dict[str, dict] = {}
        self.failing: set[str] = set()

    def requested(self, path: str, language: str | None = None) -> int:
        return sum(
            1
            for r in self.requests
            if r.url.path == f"/3{path}"
            and (language is None or r.url.params.get("language") == language)
        )

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/3")
        language = request.url.params.get("language")
        if path in self.failing:
            return httpx2.Response(500, json={"status_message": "internal error"})
        if path in self.overrides:
            return httpx2.Response(200, json=self.overrides[path])

        routes = {
            "/movie/603": MOVIE_UK,
            "/movie/10378": UNTRANSLATED_MOVIE_UK,
            "/movie/41116": UKRAINIAN_MOVIE_UK,
            "/tv/1399": SERIES_UK,
            "/tv/46052": JAPANESE_SERIES_UK,
            "/tv/2000": TALK_SHOW_UK,
            "/tv/3000": LONG_SERIES_UK,
            "/movie/popular": POPULAR_MOVIES.get(int(request.url.params.get("page", 1))),
            "/discover/movie": ANIME["movie"],
            "/discover/tv": ANIME["tv"],
            "/configuration/countries": COUNTRIES_UK if language == "uk-UA" else None,
        }
        body = SEASONS.get((path, language)) or routes.get(path)
        if body is None:
            return httpx2.Response(404, json={"status_message": "not found"})
        return httpx2.Response(200, json=body)


@pytest.fixture
def fake_tmdb() -> FakeTmdb:
    return FakeTmdb()


@pytest.fixture
def adapter(fake_tmdb: FakeTmdb) -> TmdbAdapter:
    return TmdbAdapter(TmdbClient("test-token", transport=httpx2.MockTransport(fake_tmdb)))


def make_service(adapter: TmdbAdapter, session: Session, **options) -> CatalogImportService:
    return CatalogImportService(
        adapter,
        TitleRepository(session),
        GenreRepository(session),
        CountryRepository(session),
        **options,
    )


@pytest.fixture
def service(adapter: TmdbAdapter, session: Session) -> CatalogImportService:
    return make_service(adapter, session)


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


# --- Adapter: basic conversion -----------------------------------------------


def test_client_requires_token() -> None:
    with pytest.raises(TmdbError):
        TmdbClient("")


def test_client_sends_bearer_token_and_asks_for_translations(
    adapter: TmdbAdapter, fake_tmdb: FakeTmdb
) -> None:
    adapter.get_movie(603)

    request = fake_tmdb.requests[0]
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.url.params["append_to_response"] == "translations"


def test_adapter_converts_movie_to_domain_data(adapter: TmdbAdapter) -> None:
    movie = adapter.get_movie(603)

    assert movie.type is TitleType.MOVIE
    assert movie.title == "Матриця"
    assert movie.description == "Хакер Нео дізнається правду."
    assert movie.release_year == 1999
    assert movie.rating == Decimal("8.2")
    assert movie.duration == 136
    assert movie.poster_url == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert movie.backdrop_url == "https://image.tmdb.org/t/p/w1280/backdrop.jpg"
    assert [g.name for g in movie.genres] == ["Бойовик", "Фантастика"]
    assert [(c.code, c.name) for c in movie.countries] == [("US", "США")]


def test_adapter_converts_series_and_skips_specials(adapter: TmdbAdapter) -> None:
    series = adapter.get_series(1399)

    assert series.type is TitleType.SERIES
    assert series.title == "Гра престолів"
    assert series.release_year == 2011
    assert series.duration == 60
    assert [s.number for s in series.seasons] == [1, 2]
    # Only the code is in "origin_country"; the name comes from the localized list.
    assert [(c.code, c.name) for c in series.countries] == [("US", "США")]


# --- Adapter: Ukrainian -> English -> original fallback -------------------------


def test_untranslated_movie_uses_english_us_texts_from_one_request(
    adapter: TmdbAdapter, fake_tmdb: FakeTmdb
) -> None:
    movie = adapter.get_movie(10378)

    assert movie.title == "Big Buck Bunny"  # en-US preferred over en-GB
    assert movie.description == "A giant rabbit."
    assert fake_tmdb.requested("/movie/10378") == 1


def test_series_with_non_latin_original_title_gets_english_title(adapter: TmdbAdapter) -> None:
    series = adapter.get_series(46052)

    assert series.title == "Doctor-X: Surgeon Michiko Daimon"
    assert series.description == "A surgeon."


def test_ukrainian_original_keeps_ukrainian_title(adapter: TmdbAdapter) -> None:
    movie = adapter.get_movie(41116)

    assert movie.title == "Тіні забутих предків"
    assert movie.description == "Карпатська легенда."


def test_untranslated_episodes_take_english_names_and_overviews(adapter: TmdbAdapter) -> None:
    first, second = adapter.get_series(46052).seasons[0].episodes

    assert (first.name, first.description) == ("OPE.1", "First operation.")
    # English is a placeholder too, so the Ukrainian one stays.
    assert (second.name, second.description) == ("Серія 2", "")


def test_english_season_is_loaded_only_when_needed(
    adapter: TmdbAdapter, fake_tmdb: FakeTmdb
) -> None:
    pilot, second = adapter.get_series(1399).seasons[0].episodes

    assert (pilot.name, pilot.description, pilot.duration) == ("Зима близько", "Пролог.", 62)
    assert (second.name, second.description) == ("The Kingsroad", "The Starks travel south.")
    assert fake_tmdb.requested("/tv/1399/season/1", "en-US") == 1
    assert fake_tmdb.requested("/tv/1399/season/2", "en-US") == 0  # fully translated


# --- Adapter: countries, seasons, id lists ------------------------------------


def test_adapter_loads_country_names_once(adapter: TmdbAdapter, fake_tmdb: FakeTmdb) -> None:
    adapter.get_movie(603)
    adapter.get_movie(10378)
    adapter.get_series(1399)

    assert fake_tmdb.requested("/configuration/countries") == 1
    assert [(c.code, c.name) for c in adapter.get_movie(10378).countries] == [("NL", "Нідерланди")]


def test_adapter_keeps_english_country_names_if_list_fails(
    adapter: TmdbAdapter, fake_tmdb: FakeTmdb
) -> None:
    fake_tmdb.failing.add("/configuration/countries")

    movie = adapter.get_movie(603)

    assert [(c.code, c.name) for c in movie.countries] == [("US", "United States of America")]


def test_adapter_limits_seasons(adapter: TmdbAdapter, fake_tmdb: FakeTmdb) -> None:
    series = adapter.get_series(1399, max_seasons=1)

    assert [s.number for s in series.seasons] == [1]
    assert fake_tmdb.requested("/tv/1399/season/2") == 0


def test_adapter_collects_popular_ids_across_pages(adapter: TmdbAdapter) -> None:
    assert adapter.get_popular_ids(TitleType.MOVIE, pages=2) == [603, 10378]


def test_adapter_discovers_japanese_animation(adapter: TmdbAdapter, fake_tmdb: FakeTmdb) -> None:
    assert adapter.get_anime_ids(TitleType.SERIES) == [46052]

    params = fake_tmdb.requests[-1].url.params
    assert fake_tmdb.requests[-1].url.path == "/3/discover/tv"
    assert params["with_genres"] == "16"
    assert params["with_original_language"] == "ja"
    assert params["sort_by"] == "popularity.desc"
    assert params["include_adult"] == "false"


# --- Import service --------------------------------------------------------------


def test_import_creates_titles_with_relations(
    service: CatalogImportService, session: Session
) -> None:
    report = service.import_movies([603])
    service.import_series([1399], report=report)

    assert report.created == ["Матриця (1999)", "Гра престолів (2011)"]
    assert report.failed == []
    matrix = session.scalars(select(Title).where(Title.tmdb_id == 603)).one()
    assert {g.name for g in matrix.genres} == {"Бойовик", "Фантастика"}
    assert [c.code for c in matrix.countries] == ["US"]
    assert count(session, Season) == 2
    assert count(session, Episode) == 3


def test_reimport_updates_in_place_without_duplicates(
    service: CatalogImportService, session: Session, fake_tmdb: FakeTmdb
) -> None:
    service.import_movies([603])
    service.import_series([1399])
    episode_ids = set(session.scalars(select(Episode.id)))

    fake_tmdb.overrides["/movie/603"] = {**MOVIE_UK, "vote_average": 9.0}
    report = service.import_movies([603])
    service.import_series([1399], report=report)

    assert report.created == []
    assert len(report.updated) == 2
    assert count(session, Title) == 2
    assert count(session, Genre) == 3
    assert count(session, Country) == 1
    # Episodes keep their ids, so videos attached to them stay valid.
    assert set(session.scalars(select(Episode.id))) == episode_ids
    matrix = session.scalars(select(Title).where(Title.tmdb_id == 603)).one()
    assert matrix.rating == Decimal("9.0")


def test_country_name_is_not_replaced_by_bare_code(
    service: CatalogImportService, session: Session, fake_tmdb: FakeTmdb
) -> None:
    fake_tmdb.failing.add("/configuration/countries")  # no localized names at all
    service.import_movies([603])  # US -> "United States of America"
    service.import_series([1399])  # only origin_country code "US"

    assert session.scalars(select(Country.name)).one() == "United States of America"


def test_reimport_replaces_english_country_name_with_localized(
    session: Session, fake_tmdb: FakeTmdb
) -> None:
    def import_matrix() -> None:
        client = TmdbClient("test-token", transport=httpx2.MockTransport(fake_tmdb))
        make_service(TmdbAdapter(client), session).import_movies([603])

    fake_tmdb.failing.add("/configuration/countries")
    import_matrix()
    assert session.scalars(select(Country.name)).one() == "United States of America"

    fake_tmdb.failing.clear()
    import_matrix()  # a new adapter, as in a new run of the import script
    assert session.scalars(select(Country.name)).one() == "США"


def test_failed_title_does_not_stop_batch(service: CatalogImportService, session: Session) -> None:
    report = service.import_movies([999999, 603])

    assert len(report.failed) == 1 and "999999" in report.failed[0]
    assert report.created == ["Матриця (1999)"]
    assert count(session, Title) == 1


def test_import_popular_uses_listed_ids(service: CatalogImportService, session: Session) -> None:
    report = service.import_popular(TitleType.MOVIE, pages=2)

    assert sorted(report.created) == ["Big Buck Bunny (2008)", "Матриця (1999)"]
    assert count(session, Title) == 2


def test_import_anime_uses_discovered_ids(service: CatalogImportService) -> None:
    report = service.import_anime(TitleType.SERIES, pages=1)

    assert report.created == ["Doctor-X: Surgeon Michiko Daimon (2012)"]


def test_import_skips_excluded_genres(
    adapter: TmdbAdapter, session: Session
) -> None:
    service = make_service(adapter, session, excluded_genre_ids=TMDB_NON_CINEMA_GENRE_IDS)

    report = service.import_series([2000, 1399])

    assert report.skipped == ["Вечірнє шоу: Ток-шоу"]
    assert report.created == ["Гра престолів (2011)"]
    assert session.scalars(select(Title.title)).all() == ["Гра престолів"]


def test_import_caps_episodes_per_season(adapter: TmdbAdapter, session: Session) -> None:
    service = make_service(adapter, session, max_episodes_per_season=3)

    service.import_series([3000])

    assert session.scalars(select(Episode.number).order_by(Episode.number)).all() == [1, 2, 3]
