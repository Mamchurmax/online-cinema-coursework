"""Admin panel API. Every endpoint requires the `admin` role.

(Pending payments live in billing.py: /admin/payments/pending and /resolve.)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import AdminUser, DbSession
from app.core.config import Settings, get_settings
from app.models import VideoAsset
from app.repositories.billing_repository import PlanRepository
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.repositories.content_repository import ContentRepository
from app.repositories.media_repository import AdRepository, VideoAssetRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdAdminRead,
    AdCreate,
    AdUpdate,
    AttachVideoRequest,
    EpisodeInput,
    PlanUpdate,
    RoleUpdate,
    SeasonInput,
    StreamRead,
    TitleInput,
    TmdbImportRequest,
    UserAdminRead,
    UserPage,
    VideoAssetAdminRead,
)
from app.schemas.billing import PlanRead
from app.schemas.catalog import EpisodeRead, SeasonRead, TitleDetail
from app.services.admin.accounts_admin import AccountsAdminService, PlanFields
from app.services.admin.catalog_admin import CatalogAdminService, TitleFields
from app.services.admin.errors import (
    AdminConflictError,
    AdminNotFoundError,
    AdminUnavailableError,
)
from app.services.importers.import_service import CatalogImportService
from app.services.importers.tmdb_adapter import TMDB_NON_CINEMA_GENRE_IDS, TmdbAdapter
from app.services.importers.tmdb_client import TmdbClient
from app.services.streaming import media_library as media
from app.services.streaming.media_library import MediaLibraryService

router = APIRouter(prefix="/admin", tags=["admin"])

_STATUS = {
    AdminNotFoundError: status.HTTP_404_NOT_FOUND,
    media.TitleNotFoundError: status.HTTP_404_NOT_FOUND,
    media.EpisodeNotFoundError: status.HTTP_404_NOT_FOUND,
    media.VideoNotFoundError: status.HTTP_404_NOT_FOUND,
    media.StreamNotFoundError: status.HTTP_404_NOT_FOUND,
    AdminConflictError: status.HTTP_409_CONFLICT,
    media.NotAMovieError: status.HTTP_409_CONFLICT,
    AdminUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}
_HANDLED = tuple(_STATUS)


def _error(exc: Exception) -> HTTPException:
    return HTTPException(_STATUS[type(exc)], str(exc) or type(exc).__name__)


# --- dependencies ------------------------------------------------------------------


def get_catalog_admin(
    db: DbSession, settings: Annotated[Settings, Depends(get_settings)]
) -> CatalogAdminService:
    titles, genres, countries = TitleRepository(db), GenreRepository(db), CountryRepository(db)

    def importer() -> CatalogImportService:
        adapter = TmdbAdapter(TmdbClient(settings.tmdb_api_token))  # Adapter from stage 2
        return CatalogImportService(
            adapter, titles, genres, countries,
            excluded_genre_ids=TMDB_NON_CINEMA_GENRE_IDS, max_episodes_per_season=100,
        )  # fmt: skip

    return CatalogAdminService(
        titles, genres, countries, ContentRepository(db),
        importer if settings.tmdb_api_token else None,
    )  # fmt: skip


def get_media_library(
    db: DbSession, settings: Annotated[Settings, Depends(get_settings)]
) -> MediaLibraryService:
    return MediaLibraryService(
        settings.hls_root, TitleRepository(db), VideoAssetRepository(db), AdRepository(db),
        ContentRepository(db),
    )  # fmt: skip


def get_accounts_admin(db: DbSession) -> AccountsAdminService:
    return AccountsAdminService(UserRepository(db), PlanRepository(db))


CatalogAdmin = Annotated[CatalogAdminService, Depends(get_catalog_admin)]
MediaLibrary = Annotated[MediaLibraryService, Depends(get_media_library)]
AccountsAdmin = Annotated[AccountsAdminService, Depends(get_accounts_admin)]


# --- titles ------------------------------------------------------------------------
# Listing and details use the public catalog API (/catalog/titles), built with the
# same CatalogQueryBuilder.


def _title_fields(body: TitleInput) -> TitleFields:
    return TitleFields(**body.model_dump())


@router.post("/titles", response_model=TitleDetail, status_code=status.HTTP_201_CREATED)
def create_title(body: TitleInput, _: AdminUser, catalog: CatalogAdmin):
    try:
        return catalog.create_title(_title_fields(body))
    except _HANDLED as exc:
        raise _error(exc) from None


@router.put("/titles/{title_id}", response_model=TitleDetail)
def update_title(title_id: int, body: TitleInput, _: AdminUser, catalog: CatalogAdmin):
    try:
        return catalog.update_title(title_id, _title_fields(body))
    except _HANDLED as exc:
        raise _error(exc) from None


@router.delete("/titles/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(title_id: int, _: AdminUser, catalog: CatalogAdmin):
    try:
        catalog.delete_title(title_id)
    except _HANDLED as exc:
        raise _error(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/titles/import", response_model=TitleDetail)
def import_title(body: TmdbImportRequest, _: AdminUser, catalog: CatalogAdmin):
    """Create or refresh a title from TMDB by its id."""
    try:
        return catalog.import_from_tmdb(body.tmdb_id, body.type, body.max_seasons)
    except _HANDLED as exc:
        raise _error(exc) from None


# --- seasons and episodes ---------------------------------------------------------


@router.post("/titles/{title_id}/seasons", response_model=SeasonRead,
             status_code=status.HTTP_201_CREATED)  # fmt: skip
def add_season(title_id: int, body: SeasonInput, _: AdminUser, catalog: CatalogAdmin):
    try:
        return catalog.add_season(title_id, body.number, body.name)
    except _HANDLED as exc:
        raise _error(exc) from None


@router.put("/seasons/{season_id}", response_model=SeasonRead)
def update_season(season_id: int, body: SeasonInput, _: AdminUser, catalog: CatalogAdmin):
    try:
        return catalog.update_season(season_id, body.number, body.name)
    except _HANDLED as exc:
        raise _error(exc) from None


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(season_id: int, _: AdminUser, catalog: CatalogAdmin):
    try:
        catalog.delete_season(season_id)
    except _HANDLED as exc:
        raise _error(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/seasons/{season_id}/episodes", response_model=EpisodeRead,
             status_code=status.HTTP_201_CREATED)  # fmt: skip
def add_episode(season_id: int, body: EpisodeInput, _: AdminUser, catalog: CatalogAdmin):
    try:
        return catalog.add_episode(season_id, body.model_dump())
    except _HANDLED as exc:
        raise _error(exc) from None


@router.put("/episodes/{episode_id}", response_model=EpisodeRead)
def update_episode(episode_id: int, body: EpisodeInput, _: AdminUser, catalog: CatalogAdmin):
    try:
        return catalog.update_episode(episode_id, body.model_dump())
    except _HANDLED as exc:
        raise _error(exc) from None


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(episode_id: int, _: AdminUser, catalog: CatalogAdmin):
    try:
        catalog.delete_episode(episode_id)
    except _HANDLED as exc:
        raise _error(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- videos ------------------------------------------------------------------------


def _video_read(asset: VideoAsset) -> VideoAssetAdminRead:
    episode = asset.episode
    title = asset.title if episode is None else episode.season.title
    label = None
    if episode is not None:
        label = f"S{episode.season.number}E{episode.number}: {episode.name}"
    return VideoAssetAdminRead(
        id=asset.id, hls_path=asset.hls_path, qualities=asset.qualities,
        duration_sec=asset.duration_sec, title_id=title.id, title=title.title,
        episode_label=label,
    )  # fmt: skip


@router.get("/streams", response_model=list[StreamRead])
def list_streams(_: AdminUser, library: MediaLibrary):
    """Transcoded directories under MEDIA_ROOT/hls that can be attached."""
    return library.list_streams()


@router.get("/videos", response_model=list[VideoAssetAdminRead])
def list_videos(_: AdminUser, library: MediaLibrary):
    return [_video_read(asset) for asset in library.list_videos()]


@router.put("/titles/{title_id}/video", response_model=VideoAssetAdminRead)
def attach_title_video(
    title_id: int, body: AttachVideoRequest, _: AdminUser, library: MediaLibrary
):
    try:
        return _video_read(library.attach_to_title(title_id, body.stream_dir))
    except _HANDLED as exc:
        raise _error(exc) from None


@router.put("/episodes/{episode_id}/video", response_model=VideoAssetAdminRead)
def attach_episode_video(
    episode_id: int, body: AttachVideoRequest, _: AdminUser, library: MediaLibrary
):
    try:
        return _video_read(library.attach_to_episode(episode_id, body.stream_dir))
    except _HANDLED as exc:
        raise _error(exc) from None


@router.delete("/videos/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_video(asset_id: int, _: AdminUser, library: MediaLibrary):
    try:
        library.detach(asset_id)
    except _HANDLED as exc:
        raise _error(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- ads ---------------------------------------------------------------------------


@router.get("/ads", response_model=list[AdAdminRead])
def list_ads(_: AdminUser, library: MediaLibrary):
    return library.list_ads()


@router.post("/ads", response_model=AdAdminRead, status_code=status.HTTP_201_CREATED)
def create_ad(body: AdCreate, _: AdminUser, library: MediaLibrary):
    try:
        return library.register_ad(body.name, body.stream_dir)
    except _HANDLED as exc:
        raise _error(exc) from None


@router.patch("/ads/{ad_id}", response_model=AdAdminRead)
def update_ad(ad_id: int, body: AdUpdate, _: AdminUser, library: MediaLibrary):
    try:
        return library.set_ad_active(ad_id, body.active)
    except _HANDLED as exc:
        raise _error(exc) from None


# --- plans -------------------------------------------------------------------------


@router.put("/plans/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, body: PlanUpdate, _: AdminUser, accounts: AccountsAdmin):
    try:
        return accounts.update_plan(plan_id, PlanFields(**body.model_dump()))
    except _HANDLED as exc:
        raise _error(exc) from None


# --- users -------------------------------------------------------------------------


@router.get("/users", response_model=UserPage)
def list_users(
    _: AdminUser,
    accounts: AccountsAdmin,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = accounts.search_users(q, page, page_size)
    return UserPage(items=items, total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}", response_model=UserAdminRead)
def set_user_role(user_id: int, body: RoleUpdate, admin: AdminUser, accounts: AccountsAdmin):
    try:
        return accounts.set_role(admin, user_id, body.role)
    except _HANDLED as exc:
        raise _error(exc) from None


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: AdminUser, accounts: AccountsAdmin):
    try:
        accounts.delete_user(admin, user_id)
    except _HANDLED as exc:
        raise _error(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
