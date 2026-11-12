"""Endpoints about the authenticated user: profile and watch history."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.repositories.history_repository import WatchHistoryRepository
from app.repositories.media_repository import VideoAssetRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.history import HistoryEntry, ProgressUpdate
from app.schemas.notification import MarkReadRequest, NotificationList, UnreadCount
from app.schemas.user import UserRead
from app.services.events.setup import build_event_bus
from app.services.history.history_service import (
    HistoryEntryNotFoundError,
    VideoNotFoundError,
    WatchHistoryService,
)
from app.services.notifications.notification_service import NotificationService

router = APIRouter(prefix="/me", tags=["me"])


def get_history_service(db: DbSession) -> WatchHistoryService:
    return WatchHistoryService(
        WatchHistoryRepository(db), VideoAssetRepository(db), events=build_event_bus(db)
    )


HistoryServiceDep = Annotated[WatchHistoryService, Depends(get_history_service)]


def get_notification_service(db: DbSession) -> NotificationService:
    return NotificationService(NotificationRepository(db))


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("", response_model=UserRead)
def read_me(user: CurrentUser):
    return user


@router.get("/history", response_model=list[HistoryEntry])
def read_history(
    user: CurrentUser, history: HistoryServiceDep, limit: Annotated[int, Query(ge=1, le=200)] = 50
):
    """Everything the user has watched, latest first."""
    return [HistoryEntry.from_entry(entry) for entry in history.history(user, limit)]


@router.get("/continue-watching", response_model=list[HistoryEntry])
def continue_watching(
    user: CurrentUser, history: HistoryServiceDep, limit: Annotated[int, Query(ge=1, le=50)] = 12
):
    """Started but unfinished videos, latest first."""
    return [HistoryEntry.from_entry(entry) for entry in history.continue_watching(user, limit)]


@router.put("/history/{video_asset_id}", response_model=HistoryEntry)
def save_progress(
    video_asset_id: int, body: ProgressUpdate, user: CurrentUser, history: HistoryServiceDep
):
    """Called by the player every few seconds and when playback stops."""
    try:
        entry = history.save_progress(user, video_asset_id, body.position_sec)
    except VideoNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found") from None
    return HistoryEntry.from_entry(entry)


@router.delete("/history/{video_asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_history(video_asset_id: int, user: CurrentUser, history: HistoryServiceDep):
    try:
        history.remove(user, video_asset_id)
    except HistoryEntryNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not in your history") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notifications", response_model=NotificationList)
def read_notifications(
    user: CurrentUser,
    notifications: NotificationServiceDep,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    """Latest notifications plus the unread counter for the bell icon."""
    return NotificationList(
        items=notifications.latest(user, limit, unread_only),
        unread_count=notifications.unread_count(user),
    )


@router.post("/notifications/read", response_model=UnreadCount)
def mark_notifications_read(
    body: MarkReadRequest, user: CurrentUser, notifications: NotificationServiceDep
):
    return UnreadCount(unread_count=notifications.mark_read(user, body.ids))
