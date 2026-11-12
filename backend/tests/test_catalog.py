"""Catalog search (Builder) and the public catalog API."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Country, Episode, Genre, Season, Title, TitleType, VideoAsset
from app.repositories.catalog_repository import TitleRepository
from app.services.catalog.query_builder import CatalogQueryBuilder, CatalogSort, SortOrder


@pytest.fixture
def catalog(session: Session) -> dict[str, Title]:
    drama, scifi, comedy = Genre(name="Драма"), Genre(name="Фантастика"), Genre(name="Комедія")
    us, ua, gb = (
        Country(code="US", name="США"),
        Country(code="UA", name="Україна"),
        Country(code="GB", name="Велика Британія"),
    )
    titles = {
        "matrix": Title(type=TitleType.MOVIE, title="Матриця", release_year=1999,
                        rating=Decimal("8.2"), genres=[scifi], countries=[us]),
        "dune": Title(type=TitleType.MOVIE, title="Дюна", release_year=2021,
                      rating=Decimal("7.8"), genres=[scifi, drama], countries=[us, gb]),
        "shadows": Title(type=TitleType.MOVIE, title="Тіні забутих предків", release_year=1965,
                         rating=Decimal("7.6"), genres=[drama], countries=[ua]),
        "unrated": Title(type=TitleType.MOVIE, title="100% комедія_тест", release_year=None,
                         rating=None, genres=[comedy], countries=[ua]),
        "series": Title(
            type=TitleType.SERIES, title="Чорне дзеркало", release_year=2011,
            rating=Decimal("8.3"), genres=[scifi, drama], countries=[gb],
            seasons=[Season(number=1, name="Сезон 1", episodes=[
                Episode(number=2, name="Друга"), Episode(number=1, name="Перша"),
            ])],
        ),
    }  # fmt: skip
    session.add_all(titles.values())
    session.commit()
    return titles


def run(session: Session, builder: CatalogQueryBuilder) -> tuple[list[str], int]:
    query = builder.build()
    items, total = TitleRepository(session).find_page(query.statement, query.count_statement)
    return [t.title for t in items], total


# --- Builder -------------------------------------------------------------------


def test_builder_without_steps_returns_all_sorted_by_rating(session: Session, catalog) -> None:
    titles, total = run(session, CatalogQueryBuilder())

    assert total == 5
    assert titles == [
        "Чорне дзеркало", "Матриця", "Дюна", "Тіні забутих предків", "100% комедія_тест"
    ]


def test_builder_combines_filters(session: Session, catalog) -> None:
    builder = (
        CatalogQueryBuilder()
        .with_type(TitleType.MOVIE)
        .with_genres([catalog["dune"].genres[0].id])  # фантастика
        .released_between(2000, None)
    )

    assert run(session, builder) == (["Дюна"], 1)


def test_builder_genre_and_country_lists_mean_any_of(session: Session, catalog) -> None:
    builder = (
        CatalogQueryBuilder()
        .with_countries(["ua", "GB"])
        .sorted_by(CatalogSort.TITLE, SortOrder.ASC)
    )
    titles, _ = run(session, builder)

    assert titles == ["100% комедія_тест", "Дюна", "Тіні забутих предків", "Чорне дзеркало"]


def test_builder_text_search_treats_wildcards_literally(session: Session, catalog) -> None:
    assert run(session, CatalogQueryBuilder().with_text("Матр")) == (["Матриця"], 1)
    assert run(session, CatalogQueryBuilder().with_text("100%")) == (["100% комедія_тест"], 1)
    assert run(session, CatalogQueryBuilder().with_text("%"))[1] == 1
    assert run(session, CatalogQueryBuilder().with_text("_"))[1] == 1
    assert run(session, CatalogQueryBuilder().with_text("   "))[1] == 5


def test_builder_sorts_nulls_last_in_both_directions(session: Session, catalog) -> None:
    asc, _ = run(session, CatalogQueryBuilder().sorted_by(CatalogSort.YEAR, SortOrder.ASC))
    desc, _ = run(session, CatalogQueryBuilder().sorted_by(CatalogSort.YEAR, SortOrder.DESC))

    assert asc[0] == "Тіні забутих предків" and asc[-1] == "100% комедія_тест"
    assert desc[0] == "Дюна" and desc[-1] == "100% комедія_тест"


def test_builder_paginates_without_overlap(session: Session, catalog) -> None:
    pages = [run(session, CatalogQueryBuilder().paginate(page, 2)) for page in (1, 2, 3)]

    assert [len(titles) for titles, _ in pages] == [2, 2, 1]
    assert all(total == 5 for _, total in pages)
    assert len({t for titles, _ in pages for t in titles}) == 5


def test_builder_clamps_pagination() -> None:
    query = CatalogQueryBuilder().paginate(0, 1000).build()

    assert (query.page, query.page_size) == (1, 100)


# --- API -----------------------------------------------------------------------


def test_search_endpoint_filters_and_paginates(client: TestClient, catalog) -> None:
    response = client.get(
        "/api/v1/catalog/titles",
        params={"country": ["GB", "US"], "min_rating": 8, "page_size": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["pages"], body["page"]) == (2, 2, 1)
    item = body["items"][0]
    assert item["title"] == "Чорне дзеркало"
    assert item["rating"] == "8.3"
    assert {g["name"] for g in item["genres"]} == {"Фантастика", "Драма"}


def test_search_endpoint_returns_empty_page(client: TestClient, catalog) -> None:
    body = client.get("/api/v1/catalog/titles", params={"q": "немає такого"}).json()

    assert (body["items"], body["total"], body["pages"]) == ([], 0, 0)


@pytest.mark.parametrize(
    "params",
    [
        {"year_from": 2020, "year_to": 2000},
        {"sort": "popularity"},
        {"type": "cartoon"},
        {"page": 0},
        {"page_size": 101},
        {"min_rating": 11},
    ],
)
def test_search_endpoint_validates_params(client: TestClient, params: dict) -> None:
    assert client.get("/api/v1/catalog/titles", params=params).status_code == 422


def test_title_endpoint_returns_details_with_ordered_episodes(
    client: TestClient, catalog
) -> None:
    response = client.get(f"/api/v1/catalog/titles/{catalog['series'].id}")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "series"
    assert [c["code"] for c in body["countries"]] == ["GB"]
    assert [e["name"] for e in body["seasons"][0]["episodes"]] == ["Перша", "Друга"]


def test_title_endpoint_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/catalog/titles/12345").status_code == 404


def test_filter_option_endpoints(client: TestClient, catalog) -> None:
    genres = client.get("/api/v1/catalog/genres").json()
    countries = client.get("/api/v1/catalog/countries").json()

    assert [g["name"] for g in genres] == ["Драма", "Комедія", "Фантастика"]
    assert {c["code"] for c in countries} == {"US", "UA", "GB"}


def test_catalog_is_public(client: TestClient, catalog) -> None:
    """Guests browse the catalog without a token (see the Use Case diagram)."""
    assert client.get("/api/v1/catalog/titles").status_code == 200


def test_titles_report_whether_a_video_is_available(
    client: TestClient, session: Session, catalog
) -> None:
    session.add(VideoAsset(title_id=catalog["matrix"].id, hls_path="matrix/master.m3u8",
                           qualities=["720p"], duration_sec=60))  # fmt: skip
    session.commit()

    items = client.get("/api/v1/catalog/titles", params={"page_size": 100}).json()["items"]
    with_video = {item["title"] for item in items if item["has_video"]}
    detail = client.get(f"/api/v1/catalog/titles/{catalog['series'].id}").json()

    assert with_video == {"Матриця"}
    assert client.get(f"/api/v1/catalog/titles/{catalog['matrix'].id}").json()["has_video"]
    assert detail["has_video"] is False
    assert {e["has_video"] for e in detail["seasons"][0]["episodes"]} == {False}
