"""Personal recommendations (popular titles for guests)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, OptionalUser
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.catalog import TitleListItem
from app.schemas.recommendation import RecommendationRead
from app.services.recommendations.recommendation_service import RecommendationService

router = APIRouter(tags=["recommendations"])


def get_recommendation_service(db: DbSession) -> RecommendationService:
    return RecommendationService(RecommendationRepository(db))


RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]


@router.get("/recommendations", response_model=list[RecommendationRead])
def recommendations(
    user: OptionalUser,
    service: RecommendationServiceDep,
    strategy: Literal["hybrid", "genre", "popular"] = "hybrid",
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
):
    """`strategy` selects the algorithm (Strategy pattern). Guests get popular titles."""
    items = service.recommend(user, strategy if user else "popular", limit)
    return [
        RecommendationRead(
            title=TitleListItem.model_validate(item.title), score=item.score, reason=item.reason
        )
        for item in items
    ]
