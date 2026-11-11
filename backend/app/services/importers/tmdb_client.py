"""Thin HTTP client for TMDB API v3. Returns raw JSON exactly as TMDB sends it."""

from typing import Any

import httpx2

TMDB_API_URL = "https://api.themoviedb.org/3"

Json = dict[str, Any]


class TmdbError(Exception):
    pass


class TmdbClient:
    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = TMDB_API_URL,
        transport: httpx2.BaseTransport | None = None,
        timeout: float = 15.0,
    ) -> None:
        if not api_token:
            raise TmdbError("TMDB_API_TOKEN is not set (see .env.example)")
        self._http = httpx2.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
            transport=transport,
            timeout=timeout,
        )

    def get(self, path: str, **params: Any) -> Json:
        response = self._http.get(path, params=params)
        if response.status_code != 200:
            raise TmdbError(f"GET {path} -> HTTP {response.status_code}: {response.text[:200]}")
        return response.json()

    def movie(self, movie_id: int, language: str) -> Json:
        return self.get(f"/movie/{movie_id}", language=language)

    def tv(self, tv_id: int, language: str) -> Json:
        return self.get(f"/tv/{tv_id}", language=language)

    def tv_season(self, tv_id: int, season_number: int, language: str) -> Json:
        return self.get(f"/tv/{tv_id}/season/{season_number}", language=language)

    def popular(self, media: str, page: int, language: str) -> Json:
        """`media` is "movie" or "tv"."""
        return self.get(f"/{media}/popular", page=page, language=language)

    def close(self) -> None:
        self._http.close()
