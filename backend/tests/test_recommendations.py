"""Recommendations: the three strategies and the API."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Episode,
    Favorite,
    Genre,
    Season,
    Title,
    TitleType,
    User,
    VideoAsset,
    WatchHistory,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.recommendations.recommendation_service import (
    RecommendationService,
    UnknownStrategyError,
)
from app.services.recommendations.strategies import (
    GenreBasedStrategy,
    HybridStrategy,
    PopularityStrategy,
    Recommendation,
    RecommendationStrategy,
    UserProfile,
)


@pytest.fixture
def world(session: Session) -> dict:
    """Two genres, a few titles, a viewer who loves animation."""
    anim, drama, horror = Genre(name="Мультфільм"), Genre(name="Драма"), Genre(name="Жахи")

    def title(name, genres, rating, views=0, kind=TitleType.MOVIE):  # noqa: ANN001, ANN202
        return Title(type=kind, title=name, genres=genres, rating=Decimal(rating), watch_count=views)

    t = {
        "watched_anim": title("Big Buck Bunny", [anim], "6.5"),
        "anim_good": title("Віднесені привидами", [anim], "8.5"),
        "anim_ok": title("Мрія Слонів", [anim, drama], "5.8"),
        "drama_hit": title("Хрещений батько", [drama], "8.7", views=50),
        "horror_hit": title("Сяйво", [horror], "8.4", views=80),
        "saved": title("Твоє ім'я", [anim, drama], "8.5"),
        "series": Title(type=TitleType.SERIES, title="Аркейн", genres=[anim], rating=Decimal("8.8"),
                        seasons=[Season(number=1, name="С1", episodes=[Episode(number=1, name="Е1")])]),
    }  # fmt: skip
    viewer = User(email="fan@example.com", password_hash="x", display_name="Fan")
    session.add_all([*t.values(), viewer])
    session.flush()
    movie_video = VideoAsset(title_id=t["watched_anim"].id, hls_path="b.m3u8", qualities=["720p"],
                             duration_sec=100)  # fmt: skip
    episode_video = VideoAsset(episode_id=t["series"].seasons[0].episodes[0].id, hls_path="e.m3u8",
                               qualities=["720p"], duration_sec=100)  # fmt: skip
    session.add_all([movie_video, episode_video])
    session.flush()
    session.add_all([
        WatchHistory(user_id=viewer.id, video_asset_id=movie_video.id, progress_sec=100,
                     completed=True),
        WatchHistory(user_id=viewer.id, video_asset_id=episode_video.id, progress_sec=30,
                     completed=False),
        Favorite(user_id=viewer.id, title_id=t["saved"].id),
    ])  # fmt: skip
    session.commit()
    return {"titles": t, "viewer": viewer, "genres": {"anim": anim, "drama": drama}}


def names(items: list[Recommendation]) -> list[str]:
    return [item.title.title for item in items]


def test_profile_weights_finished_started_and_saved_titles(session: Session, world: dict) -> None:
    profile = RecommendationService(RecommendationRepository(session)).profile(world["viewer"])
    anim, drama = world["genres"]["anim"].id, world["genres"]["drama"].id
    t = world["titles"]

    # Big Buck Bunny finished (2) + Arcane started (1) + "Твоє ім'я" saved (1.5)
    assert profile.genre_weights[anim] == 4.5
    assert profile.genre_weights[drama] == 1.5
    assert profile.seen_title_ids == {t["watched_anim"].id, t["series"].id, t["saved"].id}
    assert profile.genre_names[anim] == "Мультфільм"


def test_genre_strategy_prefers_the_users_genres_and_skips_seen(
    session: Session, world: dict
) -> None:
    service = RecommendationService(RecommendationRepository(session))
    items = service.recommend(world["viewer"], "genre")

    # "Мрія Слонів" matches both liked genres (animation + drama), so it may even come first.
    assert set(names(items)[:2]) == {"Віднесені привидами", "Мрія Слонів"}
    assert "Сяйво" not in names(items)  # a genre the user never watched
    assert not {"Big Buck Bunny", "Аркейн", "Твоє ім'я"} & set(names(items))
    assert items[0].reason == "Бо ви дивитесь «Мультфільм»"


def test_popularity_strategy_ranks_by_finished_views(session: Session, world: dict) -> None:
    items = RecommendationService(RecommendationRepository(session)).recommend(
        world["viewer"], "popular"
    )

    assert names(items)[:2] == ["Сяйво", "Хрещений батько"]
    assert items[0].reason == "Популярне на сайті"


def test_hybrid_mixes_taste_and_popularity(session: Session, world: dict) -> None:
    items = RecommendationService(RecommendationRepository(session)).recommend(world["viewer"])

    top = names(items)
    assert top[0] in {"Віднесені привидами", "Мрія Слонів"}  # personal taste weighs most
    assert {"Сяйво", "Хрещений батько"} <= set(top)  # popular titles still appear
    assert top.index("Віднесені привидами") < top.index("Сяйво")


def test_new_user_gets_popular_titles_from_every_strategy(session: Session, world: dict) -> None:
    newcomer = User(email="new@example.com", password_hash="x", display_name="N")
    session.add(newcomer)
    session.commit()
    service = RecommendationService(RecommendationRepository(session))

    assert service.recommend(newcomer, "genre") == []
    assert names(service.recommend(newcomer, "hybrid"))[:2] == ["Сяйво", "Хрещений батько"]


def test_unknown_strategy_is_rejected(session: Session) -> None:
    with pytest.raises(UnknownStrategyError):
        RecommendationService(RecommendationRepository(session)).recommend(None, "random")


class Fixed(RecommendationStrategy):
    code = "fixed"

    def __init__(self, items: list[Recommendation]) -> None:
        self.items = items

    def recommend(self, profile: UserProfile, limit: int) -> list[Recommendation]:
        return self.items[:limit]


def test_hybrid_is_a_weighted_sum_of_its_parts() -> None:
    a, b, c = (Title(id=i, title=n) for i, n in [(1, "A"), (2, "B"), (3, "C")])
    first = Fixed([Recommendation(a, 1.0, "taste"), Recommendation(b, 0.5, "taste")])
    second = Fixed([Recommendation(b, 1.0, "popular"), Recommendation(c, 0.9, "popular")])

    items = HybridStrategy([(first, 0.7), (second, 0.3)]).recommend(UserProfile(), 10)

    assert [(i.title.title, i.score, i.reason) for i in items] == [
        ("A", 0.7, "taste"),
        ("B", 0.65, "taste"),  # 0.7*0.5 + 0.3*1.0; "taste" contributed more
        ("C", 0.27, "popular"),
    ]


def test_strategies_share_one_interface() -> None:
    for strategy in (GenreBasedStrategy, PopularityStrategy, HybridStrategy):
        assert issubclass(strategy, RecommendationStrategy)


# --- API -----------------------------------------------------------------------


def test_api_recommendations_for_user_and_guest(
    client: TestClient, session: Session, world: dict
) -> None:
    client.post("/api/v1/auth/register",
                json={"email": "api@example.com", "password": "rec-pass-123", "display_name": "A"})  # fmt: skip
    token = client.post("/api/v1/auth/login",
                        data={"username": "api@example.com", "password": "rec-pass-123"}
                        ).json()["access_token"]  # fmt: skip
    user = session.scalars(select(User).where(User.email == "api@example.com")).one()
    session.add(Favorite(user_id=user.id, title_id=world["titles"]["anim_good"].id))
    session.commit()

    personal = client.get("/api/v1/recommendations", params={"strategy": "genre"},
                          headers={"Authorization": f"Bearer {token}"}).json()  # fmt: skip
    guest = client.get("/api/v1/recommendations", params={"strategy": "genre", "limit": 2}).json()

    assert personal[0]["title"]["genres"][0]["name"] == "Мультфільм"
    assert "Віднесені привидами" not in [r["title"]["title"] for r in personal]  # already saved
    assert [r["title"]["title"] for r in guest] == ["Сяйво", "Хрещений батько"]
    assert client.get("/api/v1/recommendations", params={"strategy": "x"}).status_code == 422
