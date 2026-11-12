"""Attach transcoded HLS streams to catalog titles and register the demo ad.

Run after `import_tmdb.py` (titles must exist) and `transcode.sh` / `make_ad.sh`:

    docker compose exec backend python -m scripts.register_videos
    docker compose exec backend python -m scripts.register_videos --movie 10378 big-buck-bunny
"""

import argparse
import sys

from app.core.config import Settings
from app.core.db import SessionLocal
from app.repositories.catalog_repository import TitleRepository
from app.repositories.media_repository import AdRepository, VideoAssetRepository
from app.services.streaming.media_library import (
    MediaLibraryService,
    StreamNotFoundError,
    TitleNotFoundError,
)

# TMDB id of each Blender film -> its directory under MEDIA_ROOT/hls
DEMO_MOVIES = {
    10378: "big-buck-bunny",
    45745: "sintel",
    133701: "tears-of-steel",
    9761: "elephants-dream",
}
DEMO_AD = ("Кінотеатр Premium", "ads/demo")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register HLS streams in the database")
    parser.add_argument(
        "--movie", nargs=2, metavar=("TMDB_ID", "DIR"), help="attach one stream to a movie"
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    jobs = {int(args.movie[0]): args.movie[1]} if args.movie else DEMO_MOVIES

    failed = 0
    with SessionLocal() as db:
        library = MediaLibraryService(
            Settings.instance().hls_root,
            TitleRepository(db),
            VideoAssetRepository(db),
            AdRepository(db),
        )
        for tmdb_id, stream_dir in jobs.items():
            try:
                asset = library.attach_to_movie(tmdb_id, stream_dir)
                print(f"OK   {stream_dir}: title #{asset.title_id}, {', '.join(asset.qualities)}")
            except (StreamNotFoundError, TitleNotFoundError) as exc:
                failed += 1
                print(f"SKIP {stream_dir}: {exc}")

        if not args.movie:
            try:
                ad = library.register_ad(*DEMO_AD)
                print(f"OK   ad '{ad.name}': {ad.hls_path}")
            except StreamNotFoundError as exc:
                failed += 1
                print(f"SKIP ad: {exc}")

    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
