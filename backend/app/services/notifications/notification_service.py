"""In-app notifications shown under the bell icon."""

from collections.abc import Sequence

from app.models import Notification, NotificationType, User
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, notifications: NotificationRepository) -> None:
        self._notifications = notifications

    def notify(self, user_id: int, type_: NotificationType, message: str) -> Notification:
        notification = Notification(user_id=user_id, type=type_, message=message, is_read=False)
        self._notifications.add(notification)
        return notification

    def latest(
        self, user: User, limit: int = 30, unread_only: bool = False
    ) -> Sequence[Notification]:
        return self._notifications.list_for_user(user.id, limit, unread_only=unread_only)

    def unread_count(self, user: User) -> int:
        return self._notifications.count_unread(user.id)

    def mark_read(self, user: User, ids: list[int] | None = None) -> int:
        """Mark notifications as read (all of them when `ids` is None); return unread left."""
        self._notifications.mark_read(user.id, ids)
        return self._notifications.count_unread(user.id)
