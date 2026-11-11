"""Endpoints about the authenticated user."""

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserRead

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserRead)
def read_me(user: CurrentUser):
    return user
