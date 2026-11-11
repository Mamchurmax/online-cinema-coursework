from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Episode,
    Genre,
    Season,
    Title,
    TitleType,
    User,
    UserRole,
    VideoAsset,
)


def make_series(db: Session) -> Title:
    series = Title(
        type=TitleType.SERIES,
        title="Demo series",
        rating=Decimal("8.4"),
        genres=[Genre(name="Drama")],
        seasons=[Season(number=1, name="Season 1", episodes=[Episode(number=1, name="Pilot")])],
    )
    db.add(series)
    db.flush()
    return series


def test_enums_are_stored_by_value(session: Session) -> None:
    session.add(User(email="a@example.com", password_hash="x", display_name="A"))
    session.add(Title(type=TitleType.MOVIE, title="Demo movie"))
    session.flush()

    assert session.execute(text("SELECT role FROM users")).scalar_one() == "user"
    assert session.execute(text("SELECT type FROM titles")).scalar_one() == "movie"
    assert session.scalars(select(User)).one().role is UserRole.USER


def test_video_asset_belongs_to_title_or_episode(session: Session) -> None:
    series = make_series(session)
    episode = series.seasons[0].episodes[0]

    session.add(VideoAsset(episode_id=episode.id, hls_path="ep1/master.m3u8", duration_sec=60))
    session.flush()


@pytest.mark.parametrize("owners", ["none", "both"])
def test_video_asset_requires_exactly_one_owner(session: Session, owners: str) -> None:
    series = make_series(session)
    episode_id = series.seasons[0].episodes[0].id
    asset = (
        VideoAsset(hls_path="x.m3u8", duration_sec=1)
        if owners == "none"
        else VideoAsset(title_id=series.id, episode_id=episode_id, hls_path="x.m3u8", duration_sec=1)
    )
    session.add(asset)

    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_title_removes_seasons_and_episodes(session: Session) -> None:
    series = make_series(session)
    session.delete(series)
    session.flush()

    assert session.scalars(select(Season)).all() == []
    assert session.scalars(select(Episode)).all() == []
