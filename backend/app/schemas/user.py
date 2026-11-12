from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str  # stored value; validated on input, not re-validated on output
    display_name: str
    avatar_url: str | None
    role: UserRole
