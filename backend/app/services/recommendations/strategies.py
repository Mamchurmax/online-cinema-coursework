"""Pattern: Strategy (GoF) — how recommendations are chosen.

- Strategy:            `RecommendationStrategy` — `recommend(profile, limit)` returns scored titles.
- Concrete strategies:
    `GenreBasedStrategy` — titles of the genres the user watches and saves most;
    `PopularityStrategy` — what is watched to the end most often on the site;
    `HybridStrategy`     — mixes the results of other strategies with weights
                           (by default 70% personal genres + 30% popularity).
- Context:             `RecommendationService` — builds the user's profile, picks the
                       strategy (the client may ask for one) and returns the result.

All strategies share one interface, so the service and the API do not change when
a new algorithm (e.g. "similar users") is added.
"""

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field

from app.models import Title
from app.repositories.recommendation_repository import RecommendationRepository

# How much each kind of signal says about the user's taste.
WEIGHT_COMPLETED = 2.0
WEIGHT_STARTED = 1.0
WEIGHT_FAVORITE = 1.5

# Strategies look at a wider pool than they return, so mixing has room to choose.
POOL_FACTOR = 4


@dataclass
class UserProfile:
    """What we know about the viewer's taste."""

    genre_weights: Counter[int] = field(default_factory=Counter)  # genre id -> weight
    seen_title_ids: set[int] = field(default_factory=set)  # watched or saved: not recommended
    genre_names: dict[int, str] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.genre_weights


@dataclass(frozen=True)
class Recommendation:
    title: Title
    score: float  # 0..1, higher is better
    reason: str


class RecommendationStrategy(ABC):
    """Strategy interface."""

    code: str

    @abstractmethod
    def recommend(self, profile: UserProfile, limit: int) -> list[Recommendation]: ...


def _rating_bonus(title: Title) -> float:
    return float(title.rating or 0) / 10


class GenreBasedStrategy(RecommendationStrategy):
    """Concrete strategy: more of the genres the user likes."""

    code = "genre"

    def __init__(self, repository: RecommendationRepository) -> None:
        self._repository = repository

    def recommend(self, profile: UserProfile, limit: int) -> list[Recommendation]:
        if profile.is_empty:
            return []  # nothing known yet ("cold start")
        top_genres = {g for g, _ in profile.genre_weights.most_common(5)}
        candidates = self._repository.titles_with_genres(
            top_genres, profile.seen_title_ids, limit * POOL_FACTOR
        )
        total = sum(profile.genre_weights.values())

        scored = []
        for title in candidates:
            matched = [g.id for g in title.genres if g.id in profile.genre_weights]
            taste = sum(profile.genre_weights[g] for g in matched) / total
            # Taste decides; the rating only breaks ties between similar matches.
            score = 0.85 * min(taste, 1.0) + 0.15 * _rating_bonus(title)
            best = max(matched, key=lambda g: profile.genre_weights[g])
            reason = f"Бо ви дивитесь «{profile.genre_names.get(best, 'цей жанр')}»"
            scored.append(Recommendation(title, round(score, 4), reason))
        return sorted(scored, key=lambda r: r.score, reverse=True)[:limit]


class PopularityStrategy(RecommendationStrategy):
    """Concrete strategy: what other viewers finish most often."""

    code = "popular"

    def __init__(self, repository: RecommendationRepository) -> None:
        self._repository = repository

    def recommend(self, profile: UserProfile, limit: int) -> list[Recommendation]:
        titles = self._repository.popular_titles(profile.seen_title_ids, limit * POOL_FACTOR)
        top_views = max((t.watch_count for t in titles), default=0) or 1
        scored = [
            Recommendation(
                title,
                round(0.7 * title.watch_count / top_views + 0.3 * _rating_bonus(title), 4),
                "Популярне на сайті" if title.watch_count else "Високий рейтинг",
            )
            for title in titles
        ]
        return sorted(scored, key=lambda r: r.score, reverse=True)[:limit]


class HybridStrategy(RecommendationStrategy):
    """Concrete strategy built from other strategies: a weighted mix of their scores."""

    code = "hybrid"

    def __init__(self, parts: list[tuple[RecommendationStrategy, float]]) -> None:
        self._parts = parts

    def recommend(self, profile: UserProfile, limit: int) -> list[Recommendation]:
        scores: dict[int, float] = {}
        best: dict[int, tuple[float, Recommendation]] = {}
        for strategy, weight in self._parts:
            for item in strategy.recommend(profile, limit * POOL_FACTOR):
                key = item.title.id
                scores[key] = scores.get(key, 0.0) + weight * item.score
                # The reason shown is the one from the part that contributed most.
                if key not in best or weight * item.score > best[key][0]:
                    best[key] = (weight * item.score, item)

        merged = [
            Recommendation(best[key][1].title, round(score, 4), best[key][1].reason)
            for key, score in scores.items()
        ]
        return sorted(merged, key=lambda r: r.score, reverse=True)[:limit]
