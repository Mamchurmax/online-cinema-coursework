from decimal import Decimal
from math import ceil
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.enums import TitleType
from app.services.catalog.query_builder import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    CatalogSort,
    SortOrder,
)


class CatalogFilters(BaseModel):
    """Query parameters of GET /catalog/titles."""

    q: str | None = Field(default=None, max_length=100, description="Search in the title")
    type: TitleType | None = None
    genre: list[int] = Field(default_factory=list, description="Genre ids (any of)")
    country: list[str] = Field(default_factory=list, description="ISO country codes (any of)")
    year_from: int | None = Field(default=None, ge=1870, le=2100)
    year_to: int | None = Field(default=None, ge=1870, le=2100)
    min_rating: float | None = Field(default=None, ge=0, le=10)
    sort: CatalogSort = CatalogSort.RATING
    order: SortOrder = SortOrder.DESC
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @model_validator(mode="after")
    def check_year_range(self) -> Self:
        years = (self.year_from, self.year_to)
        if None not in years and years[0] > years[1]:
            raise ValueError("year_from must not be greater than year_to")
        return self


class GenreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class EpisodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    description: str
    duration: int | None


class SeasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    episodes: list[EpisodeRead]


class TitleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: TitleType
    title: str
    release_year: int | None
    rating: Decimal | None
    poster_url: str | None
    genres: list[GenreRead]


class TitleDetail(TitleListItem):
    description: str
    backdrop_url: str | None
    duration: int | None
    countries: list[CountryRead]
    seasons: list[SeasonRead]


class TitlePage(BaseModel):
    items: list[TitleListItem]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def pages(self) -> int:
        return ceil(self.total / self.page_size)
