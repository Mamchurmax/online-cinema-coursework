from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import TitleType, UserRole

Quality = Literal["360p", "720p", "1080p"]


class TitleInput(BaseModel):
    type: TitleType
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    release_year: int | None = Field(default=None, ge=1870, le=2100)
    rating: Decimal | None = Field(default=None, ge=0, le=10, decimal_places=1)
    poster_url: str | None = Field(default=None, max_length=500)
    backdrop_url: str | None = Field(default=None, max_length=500)
    duration: int | None = Field(default=None, ge=1, le=1000)
    genre_ids: list[int] = Field(default_factory=list)
    country_codes: list[str] = Field(default_factory=list)


class TmdbImportRequest(BaseModel):
    tmdb_id: int = Field(ge=1)
    type: TitleType
    max_seasons: int = Field(default=2, ge=1, le=20)


class SeasonInput(BaseModel):
    number: int = Field(ge=1, le=500)
    name: str = Field(min_length=1, max_length=255)


class EpisodeInput(BaseModel):
    number: int = Field(ge=1, le=10000)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    duration: int | None = Field(default=None, ge=1, le=1000)


class StreamRead(BaseModel):
    directory: str
    hls_path: str
    qualities: list[str]
    duration_sec: int


class AttachVideoRequest(BaseModel):
    stream_dir: str = Field(min_length=1, max_length=200, pattern=r"^[\w\-]+(/[\w\-]+)?$")


class VideoAssetAdminRead(BaseModel):
    id: int
    hls_path: str
    qualities: list[str]
    duration_sec: int
    title_id: int
    title: str
    episode_label: str | None


class PlanUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(ge=0, le=100000, decimal_places=2)
    period_days: int = Field(ge=1, le=366)
    max_quality: Quality
    has_ads: bool


class UserAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str  # stored value; validated on input, not re-validated on output
    display_name: str
    role: UserRole
    created_at: datetime


class UserPage(BaseModel):
    items: list[UserAdminRead]
    total: int
    page: int
    page_size: int


class RoleUpdate(BaseModel):
    role: UserRole


class AdAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hls_path: str
    active: bool


class AdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    stream_dir: str = Field(min_length=1, max_length=200, pattern=r"^[\w\-]+(/[\w\-]+)?$")


class AdUpdate(BaseModel):
    active: bool
