"""Observer: EventBus and the TitleWatched -> statistics chain."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Episode, Season, Title, TitleType, User, VideoAsset
from app.repositories.history_repository import WatchHistoryRepository
from app.repositories.media_repository import VideoAssetRepository
from app.services.events.bus import EventBus
from app.services.events.events import DomainEvent, PaymentFailed, TitleWatched
from app.services.events.setup import build_event_bus
from app.services.history.history_service import WatchHistoryService


class Recorder:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def __call__(self, event: DomainEvent) -> None:
        self.events.append(event)

    def publish(self, event: DomainEvent) -> None:  # also usable as an EventPublisher
        self.events.append(event)


def test_bus_notifies_only_subscribers_of_that_event_type() -> None:
    bus = EventBus()
    watched, failed = Recorder(), Recorder()
    bus.subscribe(TitleWatched, watched)
    bus.subscribe(PaymentFailed, failed)

    event = TitleWatched(user_id=1, title_id=2, video_asset_id=3)
    bus.publish(event)

    assert watched.events == [event]
    assert failed.events == []


def test_bus_notifies_every_observer_in_subscription_order() -> None:
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe(TitleWatched, lambda e: calls.append("first"))
    bus.subscribe(TitleWatched, lambda e: calls.append("second"))

    bus.publish(TitleWatched(user_id=1, title_id=2, video_asset_id=3))

    assert calls == ["first", "second"]


def test_unsubscribed_observer_is_not_notified() -> None:
    bus = EventBus()
    recorder = Recorder()
    bus.subscribe(TitleWatched, recorder)
    bus.unsubscribe(TitleWatched, recorder)

    bus.publish(TitleWatched(user_id=1, title_id=2, video_asset_id=3))

    assert recorder.events == []


def make_library(session: Session) -> tuple[User, VideoAsset, VideoAsset, Title, Title]:
    movie = Title(type=TitleType.MOVIE, title="Сінтел")
    series = Title(type=TitleType.SERIES, title="Серіал",
                   seasons=[Season(number=1, name="С1", episodes=[Episode(number=1, name="Е1")])])  # fmt: skip
    viewer = User(email="v@example.com", password_hash="x", display_name="V")
    session.add_all([movie, series, viewer])
    session.flush()
    movie_video = VideoAsset(title_id=movie.id, hls_path="m.m3u8", qualities=["720p"],
                             duration_sec=100)  # fmt: skip
    episode_video = VideoAsset(episode_id=series.seasons[0].episodes[0].id, hls_path="e.m3u8",
                               qualities=["720p"], duration_sec=100)  # fmt: skip
    session.add_all([movie_video, episode_video])
    session.commit()
    return viewer, movie_video, episode_video, movie, series


def test_title_watched_is_published_once_when_a_video_is_finished(session: Session) -> None:
    viewer, movie_video, episode_video, movie, series = make_library(session)
    recorder = Recorder()
    history = WatchHistoryService(WatchHistoryRepository(session), VideoAssetRepository(session),
                                  events=recorder)  # fmt: skip

    history.save_progress(viewer, movie_video.id, 50)  # not finished yet
    history.save_progress(viewer, movie_video.id, 95)  # finished
    history.save_progress(viewer, movie_video.id, 99)  # still finished: no second event
    history.save_progress(viewer, episode_video.id, 100)

    assert recorder.events == [
        TitleWatched(user_id=viewer.id, title_id=movie.id, video_asset_id=movie_video.id),
        # An episode counts as a view of its series.
        TitleWatched(user_id=viewer.id, title_id=series.id, video_asset_id=episode_video.id),
    ]


def test_statistics_listener_counts_finished_views(session: Session) -> None:
    viewer, movie_video, _, movie, _ = make_library(session)
    other = User(email="o@example.com", password_hash="x", display_name="O")
    session.add(other)
    session.commit()

    def history() -> WatchHistoryService:
        return WatchHistoryService(WatchHistoryRepository(session), VideoAssetRepository(session),
                                   events=build_event_bus(session))  # fmt: skip

    history().save_progress(viewer, movie_video.id, 100)
    history().save_progress(viewer, movie_video.id, 100)  # same viewer again: counted once
    history().save_progress(other, movie_video.id, 90)
    session.refresh(movie)

    assert movie.watch_count == 2


def test_finishing_via_api_updates_watch_count(client: TestClient, session: Session) -> None:
    _, movie_video, _, movie, _ = make_library(session)
    client.post("/api/v1/auth/register",
                json={"email": "api@example.com", "password": "api-pass-123", "display_name": "A"})  # fmt: skip
    token = client.post("/api/v1/auth/login",
                        data={"username": "api@example.com", "password": "api-pass-123"}
                        ).json()["access_token"]  # fmt: skip

    client.put(f"/api/v1/me/history/{movie_video.id}", json={"position_sec": 100},
               headers={"Authorization": f"Bearer {token}"})  # fmt: skip
    session.refresh(movie)

    assert movie.watch_count == 1
