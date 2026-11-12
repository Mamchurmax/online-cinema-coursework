"""Pattern: Proxy (GoF) — controlled access to HLS master playlists.

- Subject:      `StreamSource` — "give me the master playlist of this video".
- Real subject: `HlsFileStreamSource` — reads `master.m3u8` from disk and makes the
                variant links absolute (`/media/hls/<video>/<quality>/index.m3u8`).
- Proxy:        `StreamAccessProxy` — same interface; before touching the real source it
                asks the plan's `PlaybackPolicy` (Strategy) which qualities are allowed,
                refuses if none are, and removes the forbidden variants from the playlist.
                The player cannot even see a 1080p variant on the Free plan.

The client code (`PlaybackService`) works with `StreamSource` and does not know whether
it talks to the proxy or to the file reader.

Note: variant playlists and segments stay static files under /media/hls; the proxy
protects the entry point that a player uses to discover them.
"""

from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

from app.models import VideoAsset
from app.services.streaming.policies import PlaybackPolicy

STREAM_INFO_TAG = "#EXT-X-STREAM-INF"


class StreamUnavailableError(Exception):
    """The playlist file is missing on disk."""


class StreamAccessDeniedError(Exception):
    """The viewer's plan allows none of the qualities of this video."""


class StreamSource(ABC):
    """Subject: the common interface of the real source and the proxy."""

    @abstractmethod
    def master_playlist(self, asset: VideoAsset) -> str: ...


class HlsFileStreamSource(StreamSource):
    """Real subject: reads master playlists produced by scripts/transcode.sh."""

    def __init__(self, hls_root: Path, media_url: str) -> None:
        self._hls_root = hls_root
        self._media_url = media_url.rstrip("/")

    def master_playlist(self, asset: VideoAsset) -> str:
        path = self._hls_root / asset.hls_path
        if not path.is_file():
            raise StreamUnavailableError(asset.hls_path)

        base_url = f"{self._media_url}/{PurePosixPath(asset.hls_path).parent}"
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            is_uri = line and not line.startswith("#") and "://" not in line
            lines.append(f"{base_url}/{line}" if is_uri and not line.startswith("/") else line)
        return "\n".join(lines) + "\n"


class StreamAccessProxy(StreamSource):
    """Proxy: checks the plan and filters the master playlist of the real source."""

    def __init__(self, source: StreamSource, policy: PlaybackPolicy) -> None:
        self._source = source
        self._policy = policy

    def master_playlist(self, asset: VideoAsset) -> str:
        allowed = set(self._policy.allowed_qualities(asset.qualities))
        if not allowed:
            raise StreamAccessDeniedError(
                f"plan '{self._policy.plan.code}' allows none of {asset.qualities}"
            )
        return self._keep_variants(self._source.master_playlist(asset), allowed)

    @staticmethod
    def _keep_variants(playlist: str, allowed: set[str]) -> str:
        """Drop each `#EXT-X-STREAM-INF` tag together with the URI line that follows it."""
        result: list[str] = []
        pending_tag: str | None = None
        for line in playlist.splitlines():
            if line.startswith(STREAM_INFO_TAG):
                pending_tag = line
                continue
            if pending_tag is not None and line and not line.startswith("#"):
                quality = PurePosixPath(line.split("?")[0]).parent.name  # ".../720p/index.m3u8"
                if quality in allowed:
                    result.extend([pending_tag, line])
                pending_tag = None
                continue
            if pending_tag is None:
                result.append(line)
        return "\n".join(result).rstrip("\n") + "\n"
