from pydantic import BaseModel

from app.schemas.catalog import TitleListItem


class RecommendationRead(BaseModel):
    title: TitleListItem
    score: float
    reason: str
