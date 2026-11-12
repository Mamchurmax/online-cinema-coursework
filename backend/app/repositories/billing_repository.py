"""Data access for plans, subscriptions and payments."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Payment, PaymentStatus, Plan, Subscription, SubscriptionStatus


class PlanRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, plan_id: int) -> Plan | None:
        return self._db.get(Plan, plan_id)

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

    def add(self, subscription: Subscription) -> None:
        """Part of the caller's transaction (activation runs inside a payment)."""
        self._db.add(subscription)
        self._db.flush()

    def list_active_expiring(self, start: datetime, end: datetime) -> Sequence[Subscription]:
        """Active subscriptions that end within [start, end]."""
        statement = (
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at >= start,
                Subscription.expires_at <= end,
            )
            .order_by(Subscription.expires_at)
        )
        return self._db.scalars(statement).all()

    def list_ended_but_active(self, now: datetime) -> Sequence[Subscription]:
        statement = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE, Subscription.expires_at <= now
        )
        return self._db.scalars(statement).all()

    def commit(self) -> None:
        self._db.commit()


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, payment_id: int) -> Payment | None:
        return self._db.get(Payment, payment_id)

    def add(self, payment: Payment) -> None:
        self._db.add(payment)
        self._db.flush()

    def list_for_user(self, user_id: int, limit: int = 50) -> Sequence[Payment]:
        statement = (
            select(Payment)
            .options(joinedload(Payment.plan))
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(limit)
        )
        return self._db.scalars(statement).all()

    def list_by_status(self, status: PaymentStatus, limit: int = 100) -> Sequence[Payment]:
        statement = (
            select(Payment)
            .options(joinedload(Payment.plan), joinedload(Payment.user))
            .where(Payment.status == status)
            .order_by(Payment.created_at, Payment.id)
            .limit(limit)
        )
        return self._db.scalars(statement).all()

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()
