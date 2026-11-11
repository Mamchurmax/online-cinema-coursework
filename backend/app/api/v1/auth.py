"""Registration and login."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import EmailAlreadyRegisteredError, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, auth: AuthServiceDep):
    try:
        return auth.register(body.email, body.password, body.display_name)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], auth: AuthServiceDep):
    """OAuth2 password flow: `username` holds the email (works with Swagger "Authorize")."""
    try:
        token = auth.login(form.username, form.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    return TokenResponse(access_token=token)
