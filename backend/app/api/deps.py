"""Shared FastAPI dependencies: services, current user, role checks."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService, InvalidCredentialsError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(
    db: DbSession, settings: Annotated[Settings, Depends(get_settings)]
) -> AuthService:
    return AuthService(UserRepository(db), settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], auth: AuthServiceDep
) -> User:
    try:
        return auth.get_user_by_token(token)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


CurrentUser = Annotated[User, Depends(get_current_user)]

optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_optional_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)], auth: AuthServiceDep
) -> User | None:
    """The signed-in user, or None for guests (and for invalid tokens)."""
    if not token:
        return None
    try:
        return auth.get_user_by_token(token)
    except InvalidCredentialsError:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
