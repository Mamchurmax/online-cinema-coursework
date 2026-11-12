"""Data access for HLS videos and pre-roll ads."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Ad, Episode, Season, VideoAsset


class VideoAssetRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, asset_id: int) -> VideoAsset | None:
        return self._db.get(VideoAsset, asset_id)

    def get_for_title(self, title_id: int) -> VideoAsset | None:
        statement = select(VideoAsset).where(VideoAsset.title_id == title_id)
        return self._db.scalars(statement).one_or_none()

    def get_for_episode(self, episode_id: int) -> VideoAsset | None:
        statement = select(VideoAsset).where(VideoAsset.episode_id == episode_id)
        return self._db.scalars(statement).one_or_none()

    def list_all(self) -> Sequence[VideoAsset]:
        """Every video with the movie or the episode (and its series) it belongs to."""
        statement = (
            select(VideoAsset)
            .options(
                joinedload(VideoAsset.title),
                joinedload(VideoAsset.episode).joinedload(Episode.season).joinedload(Season.title),
            )
            .order_by(VideoAsset.id)
        )
        return self._db.scalars(statement).all()

    def delete(self, asset: VideoAsset) -> None:
        self._db.delete(asset)
        self._db.commit()

    def save(self, asset: VideoAsset) -> VideoAsset:
        self._db.add(asset)
        self._db.commit()
        self._db.refresh(asset)
        return asset


class AdRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_hls_path(self, hls_path: str) -> Ad | None:
        return self._db.scalars(select(Ad).where(Ad.hls_path == hls_path)).one_or_none()

    def get(self, ad_id: int) -> Ad | None:
        return self._db.get(Ad, ad_id)

    def list_all(self) -> Sequence[Ad]:
        return self._db.scalars(select(Ad).order_by(Ad.id)).all()

    def list_active(self) -> Sequence[Ad]:
        return self._db.scalars(select(Ad).where(Ad.active.is_(True)).order_by(Ad.id)).all()

    def save(self, ad: Ad) -> Ad:
        self._db.add(ad)
        self._db.commit()
        self._db.refresh(ad)
        return ad
