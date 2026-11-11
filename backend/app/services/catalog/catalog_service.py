"""Catalog browsing: search with filters, title details, filter options."""

from collections.abc import Sequence

from app.models import Country, Genre, Title
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.schemas.catalog import CatalogFilters, TitlePage
from app.services.catalog.query_builder import CatalogQueryBuilder


class TitleNotFoundError(Exception):
    pass


class CatalogService:
    def __init__(
        self, titles: TitleRepository, genres: GenreRepository, countries: CountryRepository
    ) -> None:
        self._titles = titles
        self._genres = genres
        self._countries = countries

    def search(self, filters: CatalogFilters) -> TitlePage:
        """Director of the Builder pattern: turns API filters into builder steps."""
        query = (
            CatalogQueryBuilder()
            .with_text(filters.q)
            .with_type(filters.type)
            .with_genres(filters.genre)
            .with_countries(filters.country)
            .released_between(filters.year_from, filters.year_to)
            .with_min_rating(filters.min_rating)
            .sorted_by(filters.sort, filters.order)
            .paginate(filters.page, filters.page_size)
            .build()
        )
        items, total = self._titles.find_page(query.statement, query.count_statement)
        return TitlePage.model_validate(
            {"items": items, "total": total, "page": query.page, "page_size": query.page_size},
            from_attributes=True,
        )

    def get_title(self, title_id: int) -> Title:
        title = self._titles.get_with_details(title_id)
        if title is None:
            raise TitleNotFoundError(title_id)
        return title

    def list_genres(self) -> Sequence[Genre]:
        return self._genres.list_all()

    def list_countries(self) -> Sequence[Country]:
        return self._countries.list_all()
