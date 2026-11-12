"""Starting playback: which video, which qualities, whether an ad goes first."""

import random
from dataclasses import dataclass

from app.core.config import Settings
from app.models import User, VideoAsset
from app.repositories.media_repository import AdRepository, VideoAssetRepository
from app.services.billing.plan_service import PlanService
from app.services.streaming.access_proxy import (
    HlsFileStreamSource,
    StreamAccessProxy,
    StreamSource,
)
from app.services.streaming.policies import PlaybackPolicy, policy_for_plan


class VideoNotFoundError(Exception):
    """The title or episode has no video yet."""


@dataclass(frozen=True)
class AdInfo:
    name: str
    url: str


@dataclass(frozen=True)
class PlaybackSession:
    asset_id: int
    master_url: str
    duration_sec: int
    qualities: list[str]  # what this viewer can stream
    locked_qualities: list[str]  # what a better plan would unlock
    plan_code: str
    plan_name: str
    max_quality: str
    ad: AdInfo | None


class PlaybackService:
    def __init__(
        self,
        videos: VideoAssetRepository,
        ads: AdRepository,
        plans: PlanService,
        settings: Settings,
    ) -> None:
        self._videos = videos
        self._ads = ads
        self._plans = plans
        self._settings = settings

    def start_title(self, user: User, title_id: int) -> PlaybackSession:
        return self._start(user, self._videos.get_for_title(title_id))

    def start_episode(self, user: User, episode_id: int) -> PlaybackSession:
        return self._start(user, self._videos.get_for_episode(episode_id))

    def master_playlist(self, user: User, asset_id: int) -> str:
        asset = self._videos.get(asset_id)
        if asset is None:
            raise VideoNotFoundError(asset_id)
        return self._stream_source(self._policy(user)).master_playlist(asset)

    # --- internals ------------------------------------------------------------

    def _start(self, user: User, asset: VideoAsset | None) -> PlaybackSession:
        if asset is None:
            raise VideoNotFoundError
        policy = self._policy(user)
        allowed = policy.allowed_qualities(asset.qualities)
        return PlaybackSession(
            asset_id=asset.id,
            master_url=f"{self._settings.api_v1_prefix}/playback/assets/{asset.id}/master.m3u8",
            duration_sec=asset.duration_sec,
            qualities=allowed,
            locked_qualities=[q for q in asset.qualities if q not in allowed],
            plan_code=policy.plan.code,
            plan_name=policy.plan.name,
            max_quality=policy.max_quality,
            ad=self._pick_ad() if policy.requires_preroll_ad() else None,
        )

    def _policy(self, user: User) -> PlaybackPolicy:
        return policy_for_plan(self._plans.current_plan(user.id))

    def _stream_source(self, policy: PlaybackPolicy) -> StreamSource:
        real = HlsFileStreamSource(self._settings.hls_root, self._settings.media_url)
        return StreamAccessProxy(real, policy)

    def _pick_ad(self) -> AdInfo | None:
        ads = self._ads.list_active()
        if not ads:
            return None  # no ads configured: Free viewers simply start the video
        ad = random.choice(ads)
        return AdInfo(name=ad.name, url=f"{self._settings.media_url}/{ad.hls_path}")
