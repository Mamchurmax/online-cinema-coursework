from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    """Data access for `User`. Contains no business rules."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._db.scalars(select(User).where(User.email == email)).one_or_none()

    def save(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
