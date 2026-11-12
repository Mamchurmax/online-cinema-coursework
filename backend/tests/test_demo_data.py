"""scripts.demo_data: adds consistent activity and removes all of it."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Favorite,
    Payment,
    PaymentStatus,
    Plan,
    Subscription,
    Title,
    TitleType,
    User,
    VideoAsset,
    WatchHistory,
)
from scripts import demo_data

NOW = datetime(2026, 11, 12, 12, tzinfo=UTC)


def count(session: Session, model) -> int:  # noqa: ANN001
    return session.scalar(select(func.count()).select_from(model))


def test_demo_data_is_added_once_and_removed_completely(session: Session) -> None:
    owner = User(email="owner@example.com", password_hash="x", display_name="Owner")
    titles = [Title(type=TitleType.MOVIE, title=f"Film {i}", watch_count=5) for i in range(3)]
    session.add_all([owner, *titles,
                     Plan(code="premium", name="Premium", price=Decimal(149), period_days=30,
                          max_quality="1080p", has_ads=False)])  # fmt: skip
    session.flush()
    session.add_all([VideoAsset(title_id=t.id, hls_path="m.m3u8", qualities=["720p"],
                                duration_sec=600) for t in titles])  # fmt: skip
    session.commit()

    demo_data.add(session, NOW)
    demo_data.add(session, NOW)  # second run does nothing

    demo_users = session.scalars(select(User).where(User.email.endswith("@demo.local"))).all()
    assert len(demo_users) == len(demo_data.NAMES)
    assert count(session, WatchHistory) > 0 and count(session, Favorite) > 0
    statuses = set(session.scalars(select(Payment.status)))
    assert PaymentStatus.SUCCEEDED in statuses
    assert count(session, Subscription) == session.scalar(
        select(func.count()).where(Payment.status == PaymentStatus.SUCCEEDED))
    finished = session.scalar(select(func.count()).where(WatchHistory.completed))
    assert sum(t.watch_count for t in session.scalars(select(Title))) == 15 + finished

    demo_data.remove(session)

    assert session.scalars(select(User.email)).all() == ["owner@example.com"]
    for model in (WatchHistory, Favorite, Payment, Subscription):
        assert count(session, model) == 0
    assert [t.watch_count for t in session.scalars(select(Title))] == [5, 5, 5]
