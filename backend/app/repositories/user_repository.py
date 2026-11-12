from collections.abc import Sequence

from sqlalchemy import exists, func, or_, select, true
from sqlalchemy.orm import Session

from app.models import Payment, User


class UserRepository:
    """Data access for `User`. Contains no business rules."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._db.scalars(select(User).where(User.email == email)).one_or_none()

    def search(self, query: str | None, offset: int, limit: int) -> tuple[Sequence[User], int]:
        """Users whose email or name contains `query`, newest first, plus the total."""
        condition = true()
        if query:
            pattern = f"%{query.strip()}%"
            condition = or_(User.email.ilike(pattern), User.display_name.ilike(pattern))
        items = self._db.scalars(
            select(User).where(condition).order_by(User.created_at.desc(), User.id.desc())
            .offset(offset).limit(limit)
        ).all()  # fmt: skip
        total = self._db.scalar(select(func.count()).select_from(User).where(condition)) or 0
        return items, total

    def has_payments(self, user_id: int) -> bool:
        return bool(self._db.scalar(select(exists().where(Payment.user_id == user_id))))

    def delete(self, user: User) -> None:
        self._db.delete(user)
        self._db.commit()

    def save(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
