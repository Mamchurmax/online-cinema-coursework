"""Watch history: saving progress, resume position, continue watching, API."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Episode, Season, Title, TitleType, User, VideoAsset
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.repositories.history_repository import WatchHistoryRepository
from app.repositories.media_repository import VideoAssetRepository
from app.services.billing.plan_service import PlanService
from app.services.history.history_service import (
    HistoryEntryNotFoundError,
    VideoNotFoundError,
    WatchHistoryService,
)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 12, 1, 20, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)  # every call is a bit later
        return self.now


@pytest.fixture
def library(session: Session) -> dict:
    movie = Title(type=TitleType.MOVIE, title="Сінтел", poster_url="/p.jpg")
    other = Title(type=TitleType.MOVIE, title="Big Buck Bunny")
    series = Title(
        type=TitleType.SERIES,
        title="Серіал",
        seasons=[Season(number=2, name="Сезон 2", episodes=[Episode(number=3, name="Третій")])],
    )
    viewer = User(email="viewer@example.com", password_hash="x", display_name="Viewer")
    session.add_all([movie, other, series, viewer])
    session.flush()
    episode = series.seasons[0].episodes[0]
    videos = [
        VideoAsset(title_id=movie.id, hls_path="a/m.m3u8", qualities=["720p"], duration_sec=1000),
        VideoAsset(title_id=other.id, hls_path="b/m.m3u8", qualities=["720p"], duration_sec=600),
        VideoAsset(episode_id=episode.id, hls_path="c/m.m3u8", qualities=["720p"], duration_sec=1500),
    ]
    session.add_all(videos)
    session.commit()
    return {"viewer": viewer, "movie": videos[0], "other": videos[1], "episode": videos[2]}


@pytest.fixture
def history(session: Session) -> WatchHistoryService:
    return WatchHistoryService(
        WatchHistoryRepository(session), VideoAssetRepository(session), clock=Clock()
    )


def test_progress_is_saved_and_updated(history: WatchHistoryService, library: dict) -> None:
    viewer, movie = library["viewer"], library["movie"]

    first = history.save_progress(viewer, movie.id, 120)
    second = history.save_progress(viewer, movie.id, 300)

    assert second.id == first.id
    assert (second.progress_sec, second.completed) == (300, False)
    assert history.resume_position(viewer, movie.id) == 300


def test_position_is_clamped_to_video_length(history: WatchHistoryService, library: dict) -> None:
    entry = history.save_progress(library["viewer"], library["movie"].id, 99_999)

    assert entry.progress_sec == 1000


def test_video_counts_as_watched_after_90_percent(
    history: WatchHistoryService, library: dict
) -> None:
    viewer, movie = library["viewer"], library["movie"]

    assert history.save_progress(viewer, movie.id, 899).completed is False
    assert history.save_progress(viewer, movie.id, 900).completed is True
    # Opening it again later does not make it "unwatched".
    assert history.save_progress(viewer, movie.id, 30).completed is True


@pytest.mark.parametrize(("position", "resume"), [(5, 0), (10, 10), (899, 899), (950, 0)])
def test_resume_position_skips_barely_started_and_finished(
    history: WatchHistoryService, library: dict, position: int, resume: int
) -> None:
    viewer, movie = library["viewer"], library["movie"]
    history.save_progress(viewer, movie.id, position)

    assert history.resume_position(viewer, movie.id) == resume


def test_resume_position_for_unwatched_video_is_zero(
    history: WatchHistoryService, library: dict
) -> None:
    assert history.resume_position(library["viewer"], library["movie"].id) == 0


def test_continue_watching_lists_unfinished_latest_first(
    history: WatchHistoryService, library: dict
) -> None:
    viewer = library["viewer"]
    history.save_progress(viewer, library["movie"].id, 200)
    history.save_progress(viewer, library["episode"].id, 100)
    history.save_progress(viewer, library["other"].id, 590)  # finished
    history.save_progress(viewer, library["movie"].id, 250)  # watched again: now the latest

    unfinished = history.continue_watching(viewer)
    everything = history.history(viewer)

    assert [e.video_asset_id for e in unfinished] == [library["movie"].id, library["episode"].id]
    assert [e.video_asset_id for e in everything] == [
        library["movie"].id,
        library["other"].id,
        library["episode"].id,
    ]


def test_unknown_video_and_missing_entry_are_reported(
    history: WatchHistoryService, library: dict
) -> None:
    with pytest.raises(VideoNotFoundError):
        history.save_progress(library["viewer"], 999, 10)
    with pytest.raises(HistoryEntryNotFoundError):
        history.remove(library["viewer"], library["movie"].id)


# --- API -----------------------------------------------------------------------


def login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register",
                json={"email": email, "password": "viewer-pass-1", "display_name": "V"})  # fmt: skip
    token = client.post(
        "/api/v1/auth/login", data={"username": email, "password": "viewer-pass-1"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_history_api_round_trip(client: TestClient, library: dict) -> None:
    headers = login(client, "api@example.com")
    movie, episode = library["movie"], library["episode"]

    saved = client.put(f"/api/v1/me/history/{movie.id}", json={"position_sec": 321},
                       headers=headers)  # fmt: skip
    client.put(f"/api/v1/me/history/{episode.id}", json={"position_sec": 60}, headers=headers)

    assert saved.status_code == 200
    assert saved.json() | {"last_watched_at": None} == {
        "video_asset_id": movie.id,
        "title_id": movie.title_id,
        "title": "Сінтел",
        "type": "movie",
        "poster_url": "/p.jpg",
        "backdrop_url": None,
        "episode": None,
        "progress_sec": 321,
        "duration_sec": 1000,
        "completed": False,
        "last_watched_at": None,
    }

    entries = client.get("/api/v1/me/continue-watching", headers=headers).json()
    assert [e["title"] for e in entries] == ["Серіал", "Сінтел"]
    assert entries[0]["episode"] == {"id": entries[0]["episode"]["id"], "season_number": 2,
                                     "number": 3, "name": "Третій"}  # fmt: skip

    removed = client.delete(f"/api/v1/me/history/{movie.id}", headers=headers)
    assert removed.status_code == 204
    assert [e["title"] for e in client.get("/api/v1/me/history", headers=headers).json()] == [
        "Серіал"
    ]


def test_history_is_private_and_validated(client: TestClient, library: dict) -> None:
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    client.put(f"/api/v1/me/history/{library['movie'].id}", json={"position_sec": 100},
               headers=alice)  # fmt: skip

    assert client.get("/api/v1/me/history", headers=bob).json() == []
    assert client.get("/api/v1/me/history").status_code == 401
    assert client.put(f"/api/v1/me/history/{library['movie'].id}", json={"position_sec": -1},
                      headers=alice).status_code == 422  # fmt: skip
    assert client.put("/api/v1/me/history/999", json={"position_sec": 1},
                      headers=alice).status_code == 404  # fmt: skip


def test_playback_info_contains_resume_position(
    client: TestClient, library: dict, session: Session
) -> None:
    PlanService(PlanRepository(session), SubscriptionRepository(session)).ensure_default_plans()
    headers = login(client, "resume@example.com")
    movie = library["movie"]
    client.put(f"/api/v1/me/history/{movie.id}", json={"position_sec": 432}, headers=headers)

    info = client.get(f"/api/v1/playback/titles/{movie.title_id}", headers=headers).json()

    assert info["resume_position_sec"] == 432
