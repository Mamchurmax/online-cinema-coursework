"""Registers HLS streams produced by `scripts/transcode.sh` in the database."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.models import Ad, TitleType, VideoAsset
from app.repositories.catalog_repository import TitleRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.media_repository import AdRepository, VideoAssetRepository

MASTER_PLAYLIST = "master.m3u8"


class StreamNotFoundError(Exception):
    """The HLS directory has no master playlist or meta.json."""


class TitleNotFoundError(Exception):
    pass


class EpisodeNotFoundError(Exception):
    pass


class VideoNotFoundError(Exception):
    pass


class NotAMovieError(Exception):
    """Series get their videos per episode, not on the series itself."""


@dataclass(frozen=True)
class StreamInfo:
    directory: str  # relative to the HLS root, e.g. "sintel"
    hls_path: str  # relative to the HLS root, e.g. "sintel/master.m3u8"
    qualities: list[str]
    duration_sec: int


class MediaLibraryService:
    def __init__(
        self,
        hls_root: Path,
        titles: TitleRepository,
        videos: VideoAssetRepository,
        ads: AdRepository,
        content: ContentRepository | None = None,
    ) -> None:
        self._hls_root = hls_root
        self._titles = titles
        self._videos = videos
        self._ads = ads
        self._content = content

    def read_stream(self, stream_dir: str) -> StreamInfo:
        """Validate a transcoded directory and read its meta.json."""
        directory = self._hls_root / stream_dir
        meta_file = directory / "meta.json"
        if not (directory / MASTER_PLAYLIST).is_file() or not meta_file.is_file():
            raise StreamNotFoundError(f"{directory} has no {MASTER_PLAYLIST} or meta.json")

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        return StreamInfo(
            directory=stream_dir.strip("/"),
            hls_path=f"{stream_dir.strip('/')}/{MASTER_PLAYLIST}",
            qualities=list(meta["qualities"]),
            duration_sec=int(meta["duration_sec"]),
        )

    def list_streams(self) -> list[StreamInfo]:
        """Every transcoded stream under the HLS root (one level of nesting, e.g. ads/demo)."""
        if not self._hls_root.is_dir():
            return []
        streams = []
        for meta in sorted(self._hls_root.glob("*/meta.json")) + sorted(
            self._hls_root.glob("*/*/meta.json")
        ):
            stream_dir = meta.parent.relative_to(self._hls_root).as_posix()
            try:
                streams.append(self.read_stream(stream_dir))
            except (StreamNotFoundError, ValueError, KeyError):
                continue  # half-written or broken directory: skip it
        return streams

    def attach_to_title(self, title_id: int, stream_dir: str) -> VideoAsset:
        """Create or replace the video of a movie found by its id."""
        title = self._titles.get(title_id)
        if title is None:
            raise TitleNotFoundError(title_id)
        if title.type is not TitleType.MOVIE:
            raise NotAMovieError(title_id)
        return self._attach(self._videos.get_for_title(title.id) or VideoAsset(title_id=title.id),
                            stream_dir)  # fmt: skip

    def attach_to_episode(self, episode_id: int, stream_dir: str) -> VideoAsset:
        if self._content is None or self._content.get_episode(episode_id) is None:
            raise EpisodeNotFoundError(episode_id)
        asset = self._videos.get_for_episode(episode_id) or VideoAsset(episode_id=episode_id)
        return self._attach(asset, stream_dir)

    def detach(self, asset_id: int) -> None:
        """Remove the video record; the HLS files stay on disk and can be attached again."""
        asset = self._videos.get(asset_id)
        if asset is None:
            raise VideoNotFoundError(asset_id)
        self._videos.delete(asset)

    def _attach(self, asset: VideoAsset, stream_dir: str) -> VideoAsset:
        stream = self.read_stream(stream_dir)
        asset.hls_path = stream.hls_path
        asset.qualities = stream.qualities
        asset.duration_sec = stream.duration_sec
        return self._videos.save(asset)

    def attach_to_movie(self, tmdb_id: int, stream_dir: str) -> VideoAsset:
        """Create or replace the video of a movie found by its TMDB id."""
        title = self._titles.get_by_tmdb_id(tmdb_id)
        if title is None:
            raise TitleNotFoundError(f"No title with tmdb_id={tmdb_id}; import it first")

        return self._attach(self._videos.get_for_title(title.id) or VideoAsset(title_id=title.id),
                            stream_dir)  # fmt: skip

    def list_videos(self) -> Sequence[VideoAsset]:
        return self._videos.list_all()

    def list_ads(self) -> Sequence[Ad]:
        return self._ads.list_all()

    def set_ad_active(self, ad_id: int, active: bool) -> Ad:
        ad = self._ads.get(ad_id)
        if ad is None:
            raise VideoNotFoundError(ad_id)
        ad.active = active
        return self._ads.save(ad)

    def register_ad(self, name: str, stream_dir: str) -> Ad:
        stream = self.read_stream(stream_dir)
        ad = self._ads.get_by_hls_path(stream.hls_path) or Ad(hls_path=stream.hls_path)
        ad.name = name
        ad.active = True
        return self._ads.save(ad)
