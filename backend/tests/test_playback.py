"""Playback: plan strategies (Strategy), playlist proxy (Proxy) and the playback API."""

import shutil
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    Ad,
    Plan,
    Subscription,
    SubscriptionStatus,
    Title,
    TitleType,
    User,
    VideoAsset,
)
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.services.billing.plan_service import PlanService
from app.services.streaming.access_proxy import (
    HlsFileStreamSource,
    StreamAccessDeniedError,
    StreamAccessProxy,
    StreamSource,
    StreamUnavailableError,
)
from app.services.streaming.policies import FreePolicy, PremiumPolicy, policy_for_plan

MASTER = """#EXTM3U
#EXT-X-VERSION:6
#EXT-X-STREAM-INF:BANDWIDTH=955670,RESOLUTION=640x272,CODECS="avc1.4d401e,mp4a.40.2"
360p/index.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=2883034,RESOLUTION=1280x546,CODECS="avc1.4d401f,mp4a.40.2"
720p/index.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=5010924,RESOLUTION=1920x818,CODECS="avc1.640028,mp4a.40.2"
1080p/index.m3u8
"""

FREE = Plan(code="free", name="Free", price=Decimal(0), period_days=30, max_quality="720p",
            has_ads=True)  # fmt: skip
PREMIUM = Plan(code="premium", name="Premium", price=Decimal(149), period_days=30,
               max_quality="1080p", has_ads=False)  # fmt: skip


def asset(qualities: list[str] | None = None) -> VideoAsset:
    return VideoAsset(
        id=7, hls_path="sintel/master.m3u8", qualities=qualities or ["360p", "720p", "1080p"],
        duration_sec=888,
    )  # fmt: skip


def variant_uris(playlist: str) -> list[str]:
    return [line for line in playlist.splitlines() if line and not line.startswith("#")]


@pytest.fixture
def hls_root(tmp_path: Path) -> Path:
    (tmp_path / "sintel").mkdir()
    (tmp_path / "sintel" / "master.m3u8").write_text(MASTER, encoding="utf-8")
    return tmp_path


# --- Strategy ----------------------------------------------------------------


def test_policy_is_chosen_by_ads_setting() -> None:
    assert isinstance(policy_for_plan(FREE), FreePolicy)
    assert isinstance(policy_for_plan(PREMIUM), PremiumPolicy)


def test_free_policy_limits_quality_and_requires_ad() -> None:
    policy = FreePolicy(FREE)

    assert policy.allowed_qualities(["1080p", "360p", "720p"]) == ["360p", "720p"]
    assert policy.requires_preroll_ad() is True


def test_premium_policy_allows_all_and_skips_ad() -> None:
    policy = PremiumPolicy(PREMIUM)

    assert policy.allowed_qualities(["1080p", "360p", "720p"]) == ["360p", "720p", "1080p"]
    assert policy.requires_preroll_ad() is False


def test_policy_ignores_unknown_quality_labels() -> None:
    assert FreePolicy(FREE).allowed_qualities(["hd", "360p", "4k"]) == ["360p"]


# --- Proxy ---------------------------------------------------------------------


def test_real_source_makes_variant_links_absolute(hls_root: Path) -> None:
    playlist = HlsFileStreamSource(hls_root, "/media/hls/").master_playlist(asset())

    assert variant_uris(playlist) == [
        "/media/hls/sintel/360p/index.m3u8",
        "/media/hls/sintel/720p/index.m3u8",
        "/media/hls/sintel/1080p/index.m3u8",
    ]
    assert playlist.startswith("#EXTM3U\n#EXT-X-VERSION:6\n")


def test_real_source_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StreamUnavailableError):
        HlsFileStreamSource(tmp_path, "/media/hls").master_playlist(asset())


def test_proxy_removes_variants_above_the_plan(hls_root: Path) -> None:
    proxy = StreamAccessProxy(HlsFileStreamSource(hls_root, "/media/hls"), FreePolicy(FREE))

    playlist = proxy.master_playlist(asset())

    assert variant_uris(playlist) == [
        "/media/hls/sintel/360p/index.m3u8",
        "/media/hls/sintel/720p/index.m3u8",
    ]
    assert "1920x818" not in playlist
    assert playlist.count("#EXT-X-STREAM-INF") == 2


def test_proxy_keeps_everything_for_premium(hls_root: Path) -> None:
    proxy = StreamAccessProxy(HlsFileStreamSource(hls_root, "/media/hls"), PremiumPolicy(PREMIUM))

    assert len(variant_uris(proxy.master_playlist(asset()))) == 3


class CountingSource(StreamSource):
    def __init__(self) -> None:
        self.calls = 0

    def master_playlist(self, asset: VideoAsset) -> str:
        self.calls += 1
        return MASTER


def test_proxy_denies_before_touching_the_real_source() -> None:
    real = CountingSource()
    proxy = StreamAccessProxy(real, FreePolicy(FREE))

    with pytest.raises(StreamAccessDeniedError):
        proxy.master_playlist(asset(["1080p"]))
    assert real.calls == 0


# --- API -----------------------------------------------------------------------


@pytest.fixture
def media(session: Session) -> dict:
    """Plans, a movie with a video, an ad and HLS files in the test MEDIA_ROOT."""
    plans = PlanService(PlanRepository(session), SubscriptionRepository(session))
    plans.ensure_default_plans()

    movie = Title(type=TitleType.MOVIE, title="Сінтел")
    without_video = Title(type=TitleType.MOVIE, title="Без відео")
    session.add_all([movie, without_video])
    session.flush()
    video = VideoAsset(title_id=movie.id, hls_path="sintel/master.m3u8",
                       qualities=["360p", "720p", "1080p"], duration_sec=888)  # fmt: skip
    session.add_all([video, Ad(name="Кінотеатр Premium", hls_path="ads/demo/master.m3u8")])
    session.commit()

    root = Settings.instance().hls_root
    (root / "sintel").mkdir(parents=True, exist_ok=True)
    (root / "sintel" / "master.m3u8").write_text(MASTER, encoding="utf-8")
    yield {"movie": movie, "without_video": without_video, "video": video}
    shutil.rmtree(root / "sintel")


def login(client: TestClient, email: str = "viewer@example.com") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "viewer-pass-1", "display_name": "Viewer"},
    )
    token = client.post(
        "/api/v1/auth/login", data={"username": email, "password": "viewer-pass-1"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_premium(session: Session, email: str) -> None:
    user = session.scalars(select(User).where(User.email == email)).one()
    premium = PlanRepository(session).get_by_code("premium")
    now = datetime.now(UTC)
    session.add(Subscription(user_id=user.id, plan_id=premium.id, status=SubscriptionStatus.ACTIVE,
                             started_at=now - timedelta(days=1),
                             expires_at=now + timedelta(days=29)))  # fmt: skip
    session.commit()


def test_playback_requires_login(client: TestClient, media: dict) -> None:
    movie_id, asset_id = media["movie"].id, media["video"].id

    assert client.get(f"/api/v1/playback/titles/{movie_id}").status_code == 401
    assert client.get(f"/api/v1/playback/assets/{asset_id}/master.m3u8").status_code == 401


def test_free_viewer_gets_ad_and_720p(client: TestClient, media: dict) -> None:
    headers = login(client)

    info = client.get(f"/api/v1/playback/titles/{media['movie'].id}", headers=headers).json()

    assert info["plan_code"] == "free"
    assert info["qualities"] == ["360p", "720p"]
    assert info["locked_qualities"] == ["1080p"]
    assert info["ad"] == {"name": "Кінотеатр Premium", "url": "/media/hls/ads/demo/master.m3u8"}
    assert info["master_url"] == f"/api/v1/playback/assets/{media['video'].id}/master.m3u8"

    playlist = client.get(info["master_url"], headers=headers)
    assert playlist.status_code == 200
    assert playlist.headers["content-type"].startswith("application/vnd.apple.mpegurl")
    assert variant_uris(playlist.text) == [
        "/media/hls/sintel/360p/index.m3u8",
        "/media/hls/sintel/720p/index.m3u8",
    ]


def test_premium_viewer_gets_1080p_without_ad(
    client: TestClient, media: dict, session: Session
) -> None:
    headers = login(client, "premium@example.com")
    make_premium(session, "premium@example.com")

    info = client.get(f"/api/v1/playback/titles/{media['movie'].id}", headers=headers).json()
    playlist = client.get(info["master_url"], headers=headers).text

    assert (info["plan_code"], info["ad"], info["locked_qualities"]) == ("premium", None, [])
    assert info["qualities"] == ["360p", "720p", "1080p"]
    assert variant_uris(playlist)[-1] == "/media/hls/sintel/1080p/index.m3u8"


def test_title_without_video_is_404(client: TestClient, media: dict) -> None:
    headers = login(client)

    response = client.get(f"/api/v1/playback/titles/{media['without_video'].id}", headers=headers)

    assert response.status_code == 404
    assert client.get("/api/v1/playback/assets/999/master.m3u8", headers=headers).status_code == 404


def test_video_only_in_forbidden_quality_is_403(
    client: TestClient, media: dict, session: Session
) -> None:
    media["video"].qualities = ["1080p"]
    session.commit()
    headers = login(client)

    response = client.get(f"/api/v1/playback/assets/{media['video'].id}/master.m3u8",
                          headers=headers)  # fmt: skip

    assert response.status_code == 403
