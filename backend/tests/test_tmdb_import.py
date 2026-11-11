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
from app.services.importers.tmdb_adapter import TmdbAdapter
from app.services.importers.tmdb_client import TmdbClient, TmdbError

MOVIE_UK = {
    "id": 603,
    "title": "Матриця",
    "overview": "Хакер Нео дізнається правду про реальність.",
    "release_date": "1999-03-31",
    "vote_average": 8.217,
    "poster_path": "/poster.jpg",
    "backdrop_path": "/backdrop.jpg",
    "runtime": 136,
    "genres": [{"id": 28, "name": "Бойовик"}, {"id": 878, "name": "Фантастика"}],
    "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
    "origin_country": ["US"],
}

UNTRANSLATED_MOVIE_UK = {
    "id": 10378,
    "title": "",
    "overview": "",
    "release_date": "2008-05-30",
    "vote_average": 6.4,
    "poster_path": None,
    "backdrop_path": None,
    "runtime": 10,
    "genres": [{"id": 16, "name": "Мультфільм"}],
    "production_countries": [{"iso_3166_1": "NL", "name": "Netherlands"}],
}
UNTRANSLATED_MOVIE_EN = {
    **UNTRANSLATED_MOVIE_UK,
    "title": "Big Buck Bunny",
    "overview": "A giant rabbit.",
}

SERIES_UK = {
    "id": 1399,
    "name": "Гра престолів",
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
}

SEASONS_UK = {
    1: {
        "name": "Сезон 1",
        "episodes": [
            {"episode_number": 1, "name": "Зима близько", "overview": "Пролог.", "runtime": 62},
            {"episode_number": 2, "name": "", "overview": None, "runtime": None},
        ],
    },
    2: {"name": "Сезон 2", "episodes": [{"episode_number": 1, "name": "Північ пам'ятає"}]},
}

POPULAR_MOVIES = {1: {"results": [{"id": 603}]}, 2: {"results": [{"id": 10378}]}}

COUNTRIES_UK = [
    {"iso_3166_1": "US", "english_name": "United States of America", "native_name": "США"},
    {"iso_3166_1": "NL", "english_name": "Netherlands", "native_name": "Нідерланди"},
]


class FakeTmdb:
    """Serves canned TMDB responses and records every request."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.overrides: dict[str, dict] = {}
        self.failing: set[str] = set()

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
            "/movie/10378": UNTRANSLATED_MOVIE_EN if language == "en-US" else UNTRANSLATED_MOVIE_UK,
            "/tv/1399": SERIES_UK,
            "/tv/1399/season/1": SEASONS_UK[1],
            "/tv/1399/season/2": SEASONS_UK[2],
            "/movie/popular": POPULAR_MOVIES.get(int(request.url.params.get("page", 1))),
            "/configuration/countries": COUNTRIES_UK if language == "uk-UA" else None,
        }
        body = routes.get(path)
        if body is None:
            return httpx2.Response(404, json={"status_message": "not found"})
        return httpx2.Response(200, json=body)


@pytest.fixture
def fake_tmdb() -> FakeTmdb:
    return FakeTmdb()


@pytest.fixture
def adapter(fake_tmdb: FakeTmdb) -> TmdbAdapter:
    return TmdbAdapter(TmdbClient("test-token", transport=httpx2.MockTransport(fake_tmdb)))


@pytest.fixture
def service(adapter: TmdbAdapter, session: Session) -> CatalogImportService:
    return CatalogImportService(
        adapter, TitleRepository(session), GenreRepository(session), CountryRepository(session)
    )


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


# --- Adapter -----------------------------------------------------------------


def test_client_requires_token() -> None:
    with pytest.raises(TmdbError):
        TmdbClient("")


def test_client_sends_bearer_token(adapter: TmdbAdapter, fake_tmdb: FakeTmdb) -> None:
    adapter.get_movie(603)

    assert fake_tmdb.requests[0].headers["Authorization"] == "Bearer test-token"


def test_adapter_converts_movie_to_domain_data(adapter: TmdbAdapter) -> None:
    movie = adapter.get_movie(603)

    assert movie.type is TitleType.MOVIE
    assert movie.title == "Матриця"
    assert movie.release_year == 1999
    assert movie.rating == Decimal("8.2")
    assert movie.duration == 136
    assert movie.poster_url == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert movie.backdrop_url == "https://image.tmdb.org/t/p/w1280/backdrop.jpg"
    assert [g.name for g in movie.genres] == ["Бойовик", "Фантастика"]
    assert [(c.code, c.name) for c in movie.countries] == [("US", "США")]


def test_adapter_falls_back_to_english_without_translation(
    adapter: TmdbAdapter, fake_tmdb: FakeTmdb
) -> None:
    movie = adapter.get_movie(10378)

    assert movie.title == "Big Buck Bunny"
    assert movie.description == "A giant rabbit."
    assert movie.poster_url is None
    movie_requests = [r for r in fake_tmdb.requests if r.url.path.endswith("/movie/10378")]
    assert [r.url.params["language"] for r in movie_requests] == ["uk-UA", "en-US"]


def test_adapter_converts_series_and_skips_specials(adapter: TmdbAdapter) -> None:
    series = adapter.get_series(1399)

    assert series.type is TitleType.SERIES
    assert series.release_year == 2011
    assert series.duration == 60
    assert [s.number for s in series.seasons] == [1, 2]
    pilot, second = series.seasons[0].episodes
    assert (pilot.name, pilot.duration) == ("Зима близько", 62)
    assert (second.name, second.description) == ("Епізод 2", "")
    # Only the code is in "origin_country"; the name comes from the localized list.
    assert [(c.code, c.name) for c in series.countries] == [("US", "США")]


def test_adapter_loads_country_names_once(adapter: TmdbAdapter, fake_tmdb: FakeTmdb) -> None:
    adapter.get_movie(603)
    adapter.get_movie(10378)
    adapter.get_series(1399)

    paths = [r.url.path for r in fake_tmdb.requests]
    assert paths.count("/3/configuration/countries") == 1
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
    assert not any(r.url.path.endswith("/season/2") for r in fake_tmdb.requests)


def test_adapter_collects_popular_ids_across_pages(adapter: TmdbAdapter) -> None:
    assert adapter.get_popular_ids(TitleType.MOVIE, pages=2) == [603, 10378]


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
        CatalogImportService(
            TmdbAdapter(client),
            TitleRepository(session),
            GenreRepository(session),
            CountryRepository(session),
        ).import_movies([603])

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
