"""Context of the recommendation Strategy: builds the profile and runs a strategy."""

from collections import Counter

from app.models import User
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.recommendations.strategies import (
    WEIGHT_COMPLETED,
    WEIGHT_FAVORITE,
    WEIGHT_STARTED,
    GenreBasedStrategy,
    HybridStrategy,
    PopularityStrategy,
    Recommendation,
    RecommendationStrategy,
    UserProfile,
)

DEFAULT_STRATEGY = "hybrid"


class UnknownStrategyError(Exception):
    pass


class RecommendationService:
    def __init__(self, repository: RecommendationRepository) -> None:
        self._repository = repository
        genre = GenreBasedStrategy(repository)
        popular = PopularityStrategy(repository)
        self._strategies: dict[str, RecommendationStrategy] = {
            genre.code: genre,
            popular.code: popular,
            HybridStrategy.code: HybridStrategy([(genre, 0.7), (popular, 0.3)]),
        }

    @property
    def strategy_codes(self) -> list[str]:
        return list(self._strategies)

    def recommend(
        self, user: User | None, strategy: str = DEFAULT_STRATEGY, limit: int = 12
    ) -> list[Recommendation]:
        if strategy not in self._strategies:
            raise UnknownStrategyError(strategy)
        profile = self.profile(user) if user else UserProfile()
        return self._strategies[strategy].recommend(profile, limit)

    def profile(self, user: User) -> UserProfile:
        """Genre weights from what the user watched (finished counts more) and saved."""
        signals = self._repository.viewing_signals(user.id)
        title_ids = {s.title_id for s in signals}
        genres_by_title = self._repository.genres_of(title_ids)

        weights: Counter[int] = Counter()
        for signal in signals:
            if signal.favorite:
                weight = WEIGHT_FAVORITE
            else:
                weight = WEIGHT_COMPLETED if signal.completed else WEIGHT_STARTED
            for genre_id in genres_by_title.get(signal.title_id, []):
                weights[genre_id] += weight

        return UserProfile(
            genre_weights=weights,
            seen_title_ids=title_ids,
            genre_names=self._repository.genre_names(set(weights)),
        )
