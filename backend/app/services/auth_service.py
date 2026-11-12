"""Registration, login and token-based identification of users."""

from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole
from app.repositories.user_repository import UserRepository


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self._users = users
        self._settings = settings

    def register(self, email: str, password: str, display_name: str) -> User:
        email = self._normalize_email(email)
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            role=UserRole.USER,
        )
        return self._users.save(user)

    def ensure_admin(self, email: str, password: str, display_name: str) -> tuple[User, bool]:
        """Create an administrator, or promote and re-key an existing user.

        Returns the user and whether it was newly created.
        """
        user = self._users.get_by_email(self._normalize_email(email))
        created = user is None
        if user is None:
            user = self.register(email, password, display_name)
        user.role = UserRole.ADMIN
        user.password_hash = hash_password(password)
        return self._users.save(user), created

    def login(self, email: str, password: str) -> str:
        """Check credentials and return a new access token."""
        user = self._users.get_by_email(self._normalize_email(email))
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        return create_access_token(user.id, user.role, self._settings)

    def get_user_by_token(self, token: str) -> User:
        try:
            payload = decode_access_token(token, self._settings)
        except InvalidTokenError as exc:
            raise InvalidCredentialsError from exc

        user = self._users.get_by_id(payload.user_id)
        if user is None:
            raise InvalidCredentialsError
        return user

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
