"""Registration of transcoded HLS streams and static serving of HLS files."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Ad, Title, TitleType, VideoAsset
from app.repositories.catalog_repository import TitleRepository
from app.repositories.media_repository import AdRepository, VideoAssetRepository
from app.services.streaming.media_library import (
    MediaLibraryService,
    StreamNotFoundError,
    TitleNotFoundError,
)


def make_stream(root: Path, name: str, qualities: list[str], duration: int = 596) -> None:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "master.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
    meta = {"qualities": qualities, "duration_sec": duration}
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


@pytest.fixture
def library(tmp_path: Path, session: Session) -> MediaLibraryService:
    return MediaLibraryService(
        tmp_path, TitleRepository(session), VideoAssetRepository(session), AdRepository(session)
    )


@pytest.fixture
def bunny(session: Session) -> Title:
    title = Title(type=TitleType.MOVIE, title="Big Buck Bunny", tmdb_id=10378)
    session.add(title)
    session.commit()
    return title


def test_attach_to_movie_creates_asset_from_meta(
    library: MediaLibraryService, tmp_path: Path, bunny: Title
) -> None:
    make_stream(tmp_path, "big-buck-bunny", ["360p", "720p", "1080p"])

    asset = library.attach_to_movie(10378, "big-buck-bunny")

    assert asset.title_id == bunny.id
    assert asset.hls_path == "big-buck-bunny/master.m3u8"
    assert asset.qualities == ["360p", "720p", "1080p"]
    assert asset.duration_sec == 596


def test_attach_again_replaces_stream_of_same_asset(
    library: MediaLibraryService, tmp_path: Path, session: Session, bunny: Title
) -> None:
    make_stream(tmp_path, "old", ["360p"])
    make_stream(tmp_path, "new", ["360p", "720p"], duration=600)
    first = library.attach_to_movie(10378, "old")

    second = library.attach_to_movie(10378, "new")

    assert second.id == first.id
    assert session.scalar(select(func.count()).select_from(VideoAsset)) == 1
    assert (second.hls_path, second.qualities) == ("new/master.m3u8", ["360p", "720p"])


def test_attach_requires_imported_title(library: MediaLibraryService, tmp_path: Path) -> None:
    make_stream(tmp_path, "sintel", ["360p"])

    with pytest.raises(TitleNotFoundError):
        library.attach_to_movie(45745, "sintel")


def test_attach_requires_transcoded_stream(library: MediaLibraryService, bunny: Title) -> None:
    with pytest.raises(StreamNotFoundError):
        library.attach_to_movie(10378, "missing")


def test_register_ad_is_idempotent(
    library: MediaLibraryService, tmp_path: Path, session: Session
) -> None:
    make_stream(tmp_path, "ads/demo", ["360p", "720p"], duration=10)

    library.register_ad("Old name", "ads/demo")
    ad = library.register_ad("Кінотеатр Premium", "ads/demo")

    assert session.scalar(select(func.count()).select_from(Ad)) == 1
    assert (ad.name, ad.hls_path, ad.active) == ("Кінотеатр Premium", "ads/demo/master.m3u8", True)


def test_hls_files_are_served_with_hls_content_types(client: TestClient) -> None:
    root = Settings.instance().hls_root
    stream = root / "test-stream"
    stream.mkdir(parents=True, exist_ok=True)
    try:
        (stream / "master.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
        (stream / "seg_00000.ts").write_bytes(b"\x47" * 188)

        playlist = client.get("/media/hls/test-stream/master.m3u8")
        segment = client.get("/media/hls/test-stream/seg_00000.ts")

        assert playlist.status_code == 200
        assert playlist.headers["content-type"].startswith("application/vnd.apple.mpegurl")
        assert segment.headers["content-type"] == "video/mp2t"
        assert client.get("/media/hls/../source/x.mkv").status_code == 404
    finally:
        for file in stream.iterdir():
            file.unlink()
        stream.rmdir()
