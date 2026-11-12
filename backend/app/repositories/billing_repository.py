"""Data access for plans and subscriptions."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Plan, Subscription, SubscriptionStatus


class PlanRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_code(self, code: str) -> Plan | None:
        return self._db.scalars(select(Plan).where(Plan.code == code)).one_or_none()

    def list_all(self) -> Sequence[Plan]:
        return self._db.scalars(select(Plan).order_by(Plan.price)).all()

    def save(self, plan: Plan) -> Plan:
        self._db.add(plan)
        self._db.commit()
        self._db.refresh(plan)
        return plan


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(self, user_id: int, now: datetime) -> Subscription | None:
        """The user's current subscription (the one that ends last), if any."""
        statement = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.started_at <= now,
                Subscription.expires_at > now,
            )
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        return self._db.scalars(statement).one_or_none()
