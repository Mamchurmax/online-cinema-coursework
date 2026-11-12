"""FastAPI application entry point."""

import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings

# OS mime tables do not always know HLS (".ts" may even map to a translation format).
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")
mimetypes.add_type("video/mp2t", ".ts")


def create_app() -> FastAPI:
    settings = Settings.instance()

    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # HLS variant playlists and segments. Only MEDIA_ROOT/hls is exposed, never the sources.
    app.mount(
        settings.media_url,
        StaticFiles(directory=settings.hls_root, check_dir=False),
        name="media",
    )
    return app


app = create_app()
