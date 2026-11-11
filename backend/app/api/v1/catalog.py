"""Public catalog: available to guests, no token needed."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.schemas.catalog import CatalogFilters, CountryRead, GenreRead, TitleDetail, TitlePage
from app.services.catalog.catalog_service import CatalogService, TitleNotFoundError

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_catalog_service(db: DbSession) -> CatalogService:
    return CatalogService(TitleRepository(db), GenreRepository(db), CountryRepository(db))


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get("/titles", response_model=TitlePage)
def search_titles(filters: Annotated[CatalogFilters, Query()], catalog: CatalogServiceDep):
    """Search and filter movies and series. Repeat `genre`/`country` to pass several values."""
    return catalog.search(filters)


@router.get("/titles/{title_id}", response_model=TitleDetail)
def get_title(title_id: int, catalog: CatalogServiceDep):
    try:
        return catalog.get_title(title_id)
    except TitleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Title not found"
        ) from None


@router.get("/genres", response_model=list[GenreRead])
def list_genres(catalog: CatalogServiceDep):
    return catalog.list_genres()


@router.get("/countries", response_model=list[CountryRead])
def list_countries(catalog: CatalogServiceDep):
    return catalog.list_countries()
