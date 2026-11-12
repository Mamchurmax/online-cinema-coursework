"""Pattern: Builder (GoF).

- Builder:  `CatalogQueryBuilder` — assembles a catalog search step by step
  (text, type, genres, countries, years, rating, sorting, pagination).
  Every step is optional and may be called in any order.
- Product:  `CatalogQuery` — ready-to-run SQL statements for one page of results
  and for the total count.
- Director: `CatalogService.search()` — decides which steps to call based on the
  filters received from the API.

Without the builder, one function would need a dozen optional parameters and a
tangle of `if`s; with it, each filter is a small, independently testable step.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from sqlalchemy import ColumnElement, Select, UnaryExpression, func, select
from sqlalchemy.orm import selectinload

from app.models import Country, Genre, Title, TitleType

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class CatalogSort(StrEnum):
    RATING = "rating"
    YEAR = "year"
    TITLE = "title"
    ADDED = "added"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


_SORT_COLUMNS = {
    CatalogSort.RATING: Title.rating,
    CatalogSort.YEAR: Title.release_year,
    CatalogSort.TITLE: Title.title,
    CatalogSort.ADDED: Title.created_at,
}


@dataclass(frozen=True)
class CatalogQuery:
    """Product: statements for one page of titles and for their total count."""

    statement: Select[tuple[Title]]
    count_statement: Select[tuple[int]]
    page: int
    page_size: int


class CatalogQueryBuilder:
    """Builder: each method adds one optional part of the query and returns `self`."""

    def __init__(self) -> None:
        self._conditions: list[ColumnElement[bool]] = []
        self._order_by: list[UnaryExpression] = []
        self._page = 1
        self._page_size = DEFAULT_PAGE_SIZE

    def with_text(self, text: str | None) -> Self:
        if text and text.strip():
            pattern = f"%{_escape_like(text.strip())}%"
            self._conditions.append(Title.title.ilike(pattern, escape="\\"))
        return self

    def with_type(self, title_type: TitleType | None) -> Self:
        if title_type is not None:
            self._conditions.append(Title.type == title_type)
        return self

    def with_genres(self, genre_ids: list[int] | None) -> Self:
        """Titles that have at least one of the given genres."""
        if genre_ids:
            self._conditions.append(Title.genres.any(Genre.id.in_(genre_ids)))
        return self

    def with_countries(self, country_codes: list[str] | None) -> Self:
        """Titles produced in at least one of the given countries (ISO codes)."""
        if country_codes:
            codes = [code.strip().upper() for code in country_codes]
            self._conditions.append(Title.countries.any(Country.code.in_(codes)))
        return self

    def released_between(self, year_from: int | None, year_to: int | None) -> Self:
        if year_from is not None:
            self._conditions.append(Title.release_year >= year_from)
        if year_to is not None:
            self._conditions.append(Title.release_year <= year_to)
        return self

    def with_min_rating(self, min_rating: float | None) -> Self:
        if min_rating is not None:
            self._conditions.append(Title.rating >= min_rating)
        return self

    def sorted_by(self, sort: CatalogSort, order: SortOrder = SortOrder.DESC) -> Self:
        column = _SORT_COLUMNS[sort]
        direction = column.asc() if order is SortOrder.ASC else column.desc()
        self._order_by.append(direction.nulls_last())
        return self

    def paginate(self, page: int, page_size: int = DEFAULT_PAGE_SIZE) -> Self:
        self._page = max(page, 1)
        self._page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
        return self

    def build(self) -> CatalogQuery:
        order_by = self._order_by or [Title.rating.desc().nulls_last()]
        statement = (
            select(Title)
            .where(*self._conditions)
            .options(selectinload(Title.genres), selectinload(Title.video))
            # Title.id makes the order stable, so pages never overlap.
            .order_by(*order_by, Title.id)
            .offset((self._page - 1) * self._page_size)
            .limit(self._page_size)
        )
        count_statement = select(func.count()).select_from(Title).where(*self._conditions)
        return CatalogQuery(statement, count_statement, self._page, self._page_size)


def _escape_like(text: str) -> str:
    """Treat %, _ and \\ typed by the user literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
