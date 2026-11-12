from pydantic import BaseModel, ConfigDict


class AdRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str


class PlaybackInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: int
    master_url: str
    duration_sec: int
    qualities: list[str]
    locked_qualities: list[str]
    plan_code: str
    plan_name: str
    max_quality: str
    ad: AdRead | None
    resume_position_sec: int
