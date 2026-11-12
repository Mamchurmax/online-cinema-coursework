"""Demo activity for screenshots and the report: viewers, watch history, favorites,
payments and subscriptions spread over the last weeks.

    docker compose exec backend python -m scripts.demo_data            # add
    docker compose exec backend python -m scripts.demo_data --remove   # remove everything it added

All demo users have e-mails ending in @demo.local and cannot sign in (unusable
password hash). The data is generated with a fixed seed, so it is the same every time
(relative to today). Run `register_videos` first: history needs video assets.
"""

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import (
    Favorite,
    Notification,
    NotificationType,
    Payment,
    PaymentScenario,
    PaymentStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
    Title,
    User,
    VideoAsset,
    WatchHistory,
)

DOMAIN = "@demo.local"
DAYS = 60
COMPLETED_SHARE = 0.9
NAMES = [
    "Олена", "Андрій", "Марія", "Тарас", "Ірина", "Богдан", "Софія", "Дмитро",
    "Наталія", "Остап", "Юлія", "Максим", "Христина", "Василь",
]  # fmt: skip


def is_demo():  # noqa: ANN201
    return User.email.endswith(DOMAIN)


def add(db: Session, now: datetime) -> None:
    if db.scalar(select(func.count(User.id)).where(is_demo())):
        print("Demo data already exists; run with --remove first.")
        return
    videos = db.scalars(
        select(VideoAsset).where(VideoAsset.title_id.is_not(None)).order_by(VideoAsset.id)
    ).all()
    if not videos:
        print("No movie videos: run `python -m scripts.register_videos` first.")
        return
    plans = {plan.code: plan for plan in db.scalars(select(Plan))}
    if "premium" not in plans:
        print("No plans: run `python -m scripts.seed` first.")
        return
    popular = db.scalars(
        select(Title.id).order_by(Title.rating.desc().nulls_last(), Title.id).limit(40)
    ).all()

    rng = random.Random(17)  # variant 17
    # The first videos are watched more often, so the popularity report has a leader.
    weights = {video.id: len(videos) - i for i, video in enumerate(videos)}
    completed_per_title: dict[int, int] = {}

    for i, name in enumerate(NAMES):
        joined = now - timedelta(days=rng.randint(1, DAYS), hours=rng.randint(0, 23))
        user = User(email=f"viewer{i + 1:02d}{DOMAIN}", password_hash="!demo",
                    display_name=name, created_at=joined)  # fmt: skip
        db.add(user)
        db.flush()

        count = min(len(videos), rng.choices([1, 2, 3, 4], [3, 4, 2, 1])[0])
        # Weighted sampling without replacement (Efraimidis–Spirakis keys).
        watched = sorted(videos, key=lambda v: rng.random() ** (1 / weights[v.id]))[-count:]
        for video in watched:
            done = rng.random() < 0.55
            progress = video.duration_sec if done else rng.randint(60, int(video.duration_sec * 0.8))
            moment = joined + (now - joined) * rng.random()
            db.add(WatchHistory(user_id=user.id, video_asset_id=video.id, progress_sec=progress,
                                completed=done, last_watched_at=moment))  # fmt: skip
            if done:
                completed_per_title[video.title_id] = completed_per_title.get(video.title_id, 0) + 1

        for title_id in rng.sample(popular, k=min(len(popular), rng.randint(1, 5))):
            db.add(Favorite(user_id=user.id, title_id=title_id, created_at=joined))

        if i % 3 != 2:  # two thirds try Premium
            add_payments(db, user, plans["premium"], joined, now, rng)

    for title_id, count in completed_per_title.items():
        db.execute(update(Title).where(Title.id == title_id)
                   .values(watch_count=Title.watch_count + count))  # fmt: skip
    db.commit()
    total = db.scalar(select(func.count(User.id)).where(is_demo()))
    print(f"Added {total} demo viewers ({DOMAIN}) with history, favorites and payments.")


def add_payments(db: Session, user: User, plan: Plan, joined: datetime, now: datetime,
                 rng: random.Random) -> None:  # fmt: skip
    moment = joined + timedelta(hours=rng.randint(1, 72))
    if moment >= now:
        moment = now - timedelta(minutes=5)
    outcome = rng.choices(
        [PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.PENDING], [7, 2, 1]
    )[0]
    if outcome is PaymentStatus.FAILED:  # a failed attempt, then a successful retry
        db.add(payment(user, plan, PaymentScenario.FAILED, PaymentStatus.FAILED, moment))
        moment += timedelta(minutes=rng.randint(2, 30))
        outcome = PaymentStatus.SUCCEEDED
    scenario = PaymentScenario.PENDING if outcome is PaymentStatus.PENDING else PaymentScenario.SUCCESS
    db.add(payment(user, plan, scenario, outcome, moment))
    if outcome is not PaymentStatus.SUCCEEDED:
        return

    expires = moment + timedelta(days=plan.period_days)
    status = SubscriptionStatus.ACTIVE if expires > now else SubscriptionStatus.EXPIRED
    db.add(Subscription(user_id=user.id, plan_id=plan.id, status=status, started_at=moment,
                        expires_at=expires))  # fmt: skip
    db.add(Notification(user_id=user.id, type=NotificationType.SUBSCRIPTION_ACTIVATED,
                        message=f"Підписку «{plan.name}» активовано до {expires:%d.%m.%Y}.",
                        created_at=moment))  # fmt: skip


def payment(user: User, plan: Plan, scenario: PaymentScenario, status: PaymentStatus,
            moment: datetime) -> Payment:  # fmt: skip
    return Payment(user_id=user.id, plan_id=plan.id, amount=Decimal(plan.price), provider="mock",
                   scenario=scenario, status=status, created_at=moment, updated_at=moment)  # fmt: skip


def remove(db: Session) -> None:
    demo_ids = select(User.id).where(is_demo())
    # Undo the watch_count the demo viewers added (one per completed movie).
    finished = db.execute(
        select(VideoAsset.title_id, func.count())
        .join(WatchHistory, WatchHistory.video_asset_id == VideoAsset.id)
        .where(WatchHistory.user_id.in_(demo_ids), WatchHistory.completed,
               VideoAsset.title_id.is_not(None))
        .group_by(VideoAsset.title_id)
    ).all()  # fmt: skip
    for title_id, count in finished:
        db.execute(update(Title).where(Title.id == title_id)
                   .values(watch_count=case((Title.watch_count > count, Title.watch_count - count),
                                            else_=0)))  # fmt: skip
    # Payments have no ON DELETE CASCADE (they are kept for reports), so they go first.
    payments = db.execute(delete(Payment).where(Payment.user_id.in_(demo_ids))).rowcount
    users = db.execute(delete(User).where(is_demo())).rowcount
    db.commit()
    print(f"Removed {users} demo viewers and {payments} payments "
          "(history, favorites, subscriptions and notifications are removed with them).")  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add or remove demo activity")
    parser.add_argument("--remove", action="store_true", help="remove the demo data")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    with SessionLocal() as db:
        if args.remove:
            remove(db)
        else:
            add(db, datetime.now(UTC))
    return 0


if __name__ == "__main__":
    sys.exit(main())
