"""Registers HLS streams produced by `scripts/transcode.sh` in the database."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.models import Ad, VideoAsset
from app.repositories.catalog_repository import TitleRepository
from app.repositories.media_repository import AdRepository, VideoAssetRepository

MASTER_PLAYLIST = "master.m3u8"


class StreamNotFoundError(Exception):
    """The HLS directory has no master playlist or meta.json."""


class TitleNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class StreamInfo:
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
    ) -> None:
        self._hls_root = hls_root
        self._titles = titles
        self._videos = videos
        self._ads = ads

    def read_stream(self, stream_dir: str) -> StreamInfo:
        """Validate a transcoded directory and read its meta.json."""
        directory = self._hls_root / stream_dir
        meta_file = directory / "meta.json"
        if not (directory / MASTER_PLAYLIST).is_file() or not meta_file.is_file():
            raise StreamNotFoundError(f"{directory} has no {MASTER_PLAYLIST} or meta.json")

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        return StreamInfo(
            hls_path=f"{stream_dir.strip('/')}/{MASTER_PLAYLIST}",
            qualities=list(meta["qualities"]),
            duration_sec=int(meta["duration_sec"]),
        )

    def attach_to_movie(self, tmdb_id: int, stream_dir: str) -> VideoAsset:
        """Create or replace the video of a movie found by its TMDB id."""
        title = self._titles.get_by_tmdb_id(tmdb_id)
        if title is None:
            raise TitleNotFoundError(f"No title with tmdb_id={tmdb_id}; import it first")

        stream = self.read_stream(stream_dir)
        asset = self._videos.get_for_title(title.id) or VideoAsset(title_id=title.id)
        asset.hls_path = stream.hls_path
        asset.qualities = stream.qualities
        asset.duration_sec = stream.duration_sec
        return self._videos.save(asset)

    def register_ad(self, name: str, stream_dir: str) -> Ad:
        stream = self.read_stream(stream_dir)
        ad = self._ads.get_by_hls_path(stream.hls_path) or Ad(hls_path=stream.hls_path)
        ad.name = name
        ad.active = True
        return self._ads.save(ad)
