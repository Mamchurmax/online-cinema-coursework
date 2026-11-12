from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationRead]
    unread_count: int


class MarkReadRequest(BaseModel):
    """Notification ids to mark as read; omit to mark all of them."""

    ids: list[int] | None = Field(default=None, max_length=200)


class UnreadCount(BaseModel):
    unread_count: int
