"""Playback: what to stream and the plan-filtered master playlist (login required)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import Settings, get_settings
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.repositories.media_repository import AdRepository, VideoAssetRepository
from app.schemas.playback import PlaybackInfo
from app.services.billing.plan_service import PlanNotConfiguredError, PlanService
from app.services.streaming.access_proxy import StreamAccessDeniedError, StreamUnavailableError
from app.services.streaming.playback_service import PlaybackService, VideoNotFoundError

router = APIRouter(prefix="/playback", tags=["playback"])

HLS_MEDIA_TYPE = "application/vnd.apple.mpegurl"


def get_playback_service(
    db: DbSession, settings: Annotated[Settings, Depends(get_settings)]
) -> PlaybackService:
    plans = PlanService(PlanRepository(db), SubscriptionRepository(db))
    return PlaybackService(VideoAssetRepository(db), AdRepository(db), plans, settings)


PlaybackServiceDep = Annotated[PlaybackService, Depends(get_playback_service)]

_ERRORS = {
    VideoNotFoundError: (status.HTTP_404_NOT_FOUND, "Video is not available yet"),
    StreamUnavailableError: (status.HTTP_404_NOT_FOUND, "Video files are missing"),
    StreamAccessDeniedError: (status.HTTP_403_FORBIDDEN, "Your plan does not allow this video"),
    PlanNotConfiguredError: (status.HTTP_503_SERVICE_UNAVAILABLE, "Plans are not configured"),
}


def _http_error(exc: Exception) -> HTTPException:
    code, detail = _ERRORS[type(exc)]
    return HTTPException(status_code=code, detail=detail)


@router.get("/titles/{title_id}", response_model=PlaybackInfo)
def start_title(title_id: int, user: CurrentUser, playback: PlaybackServiceDep):
    try:
        return playback.start_title(user, title_id)
    except tuple(_ERRORS) as exc:
        raise _http_error(exc) from None


@router.get("/episodes/{episode_id}", response_model=PlaybackInfo)
def start_episode(episode_id: int, user: CurrentUser, playback: PlaybackServiceDep):
    try:
        return playback.start_episode(user, episode_id)
    except tuple(_ERRORS) as exc:
        raise _http_error(exc) from None


@router.get(
    "/assets/{asset_id}/master.m3u8",
    response_class=Response,
    responses={200: {"content": {HLS_MEDIA_TYPE: {}}}},
)
def master_playlist(asset_id: int, user: CurrentUser, playback: PlaybackServiceDep):
    """Master playlist with only the qualities allowed by the viewer's plan (Proxy)."""
    try:
        playlist = playback.master_playlist(user, asset_id)
    except tuple(_ERRORS) as exc:
        raise _http_error(exc) from None
    return Response(playlist, media_type=HLS_MEDIA_TYPE, headers={"Cache-Control": "no-store"})
