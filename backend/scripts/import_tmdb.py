"""Import catalog metadata from TMDB.

Examples (run from `backend/`, or inside the container via
`docker compose exec backend python -m scripts.import_tmdb ...`):

    python -m scripts.import_tmdb                      # demo films + 1 page of popular
    python -m scripts.import_tmdb --movies 603 680     # specific movies by TMDB id
    python -m scripts.import_tmdb --series 1399 --max-seasons 1
    python -m scripts.import_tmdb --popular-movies 3 --popular-series 2
    python -m scripts.import_tmdb --anime-movies 1 --anime-series 2 --no-demo

Talk shows, soap operas, news and reality TV are skipped; long series keep at
most --max-episodes episodes per season.
"""

import argparse
import logging
import sys

import httpx2

from app.core.config import Settings
from app.core.db import SessionLocal
from app.models import TitleType
from app.repositories.catalog_repository import (
    CountryRepository,
    GenreRepository,
    TitleRepository,
)
from app.services.importers.import_service import CatalogImportService, ImportReport
from app.services.importers.tmdb_adapter import TMDB_NON_CINEMA_GENRE_IDS, TmdbAdapter
from app.services.importers.tmdb_client import TmdbClient, TmdbError

# Open Blender movies: their videos are used as demo streams.
BLENDER_MOVIES = {
    10378: "Big Buck Bunny",
    45745: "Sintel",
    133701: "Tears of Steel",
    9761: "Elephants Dream",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import titles from TMDB")
    parser.add_argument("--movies", type=int, nargs="*", default=[], help="TMDB movie ids")
    parser.add_argument("--series", type=int, nargs="*", default=[], help="TMDB TV ids")
    parser.add_argument("--popular-movies", type=int, default=0, metavar="PAGES")
    parser.add_argument("--popular-series", type=int, default=0, metavar="PAGES")
    parser.add_argument("--anime-movies", type=int, default=0, metavar="PAGES")
    parser.add_argument("--anime-series", type=int, default=0, metavar="PAGES")
    parser.add_argument(
        "--max-seasons", type=int, default=2, help="seasons to import per series (default: 2)"
    )
    parser.add_argument(
        "--max-episodes", type=int, default=100, help="episodes kept per season (default: 100)"
    )
    parser.add_argument("--no-demo", action="store_true", help="skip the Blender demo films")
    args = parser.parse_args(argv)

    nothing_requested = not (
        args.movies
        or args.series
        or args.popular_movies
        or args.popular_series
        or args.anime_movies
        or args.anime_series
    )
    if nothing_requested:
        args.popular_movies = args.popular_series = 1
    return args


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        client = TmdbClient(Settings.instance().tmdb_api_token)
    except TmdbError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    report = ImportReport()
    try:
        with SessionLocal() as db:
            service = CatalogImportService(
                TmdbAdapter(client),
                TitleRepository(db),
                GenreRepository(db),
                CountryRepository(db),
                excluded_genre_ids=TMDB_NON_CINEMA_GENRE_IDS,
                max_episodes_per_season=args.max_episodes,
            )
            movies = list(args.movies) + ([] if args.no_demo else list(BLENDER_MOVIES))
            service.import_movies(movies, report)
            service.import_series(args.series, args.max_seasons, report)
            for title_type, pages in (
                (TitleType.MOVIE, args.popular_movies),
                (TitleType.SERIES, args.popular_series),
            ):
                if pages:
                    service.import_popular(title_type, pages, args.max_seasons, report)
            for title_type, pages in (
                (TitleType.MOVIE, args.anime_movies),
                (TitleType.SERIES, args.anime_series),
            ):
                if pages:
                    service.import_anime(title_type, pages, args.max_seasons, report)
    except (TmdbError, httpx2.HTTPError) as exc:  # e.g. the popular list is unreachable
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    print(
        f"\nCreated: {len(report.created)}, updated: {len(report.updated)}, "
        f"skipped: {len(report.skipped)}, failed: {len(report.failed)}"
    )
    for line in report.skipped:
        print(f"  SKIPPED {line}")
    for line in report.failed:
        print(f"  FAILED {line}")
    return 0 if not report.failed else 2


if __name__ == "__main__":
    sys.exit(main())
