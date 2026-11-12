"""Data access for user notifications."""

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Notification


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, notification: Notification) -> None:
        """Part of the caller's transaction: event listeners must not commit on their own."""
        self._db.add(notification)
        self._db.flush()

    def list_for_user(
        self, user_id: int, limit: int, *, unread_only: bool = False
    ) -> Sequence[Notification]:
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        )
        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))
        return self._db.scalars(statement).all()

    def count_unread(self, user_id: int) -> int:
        statement = select(func.count()).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
        return self._db.scalar(statement) or 0

    def mark_read(self, user_id: int, ids: list[int] | None = None) -> None:
        """Mark the given notifications (or all of them) of this user as read."""
        statement = update(Notification).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
        if ids is not None:
            statement = statement.where(Notification.id.in_(ids))
        self._db.execute(statement.values(is_read=True))
        self._db.commit()
