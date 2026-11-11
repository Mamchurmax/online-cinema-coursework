"""Plans, subscriptions and payments."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, enum_column
from app.models.enums import PaymentScenario, PaymentStatus, SubscriptionStatus
from app.models.user import User


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)  # "free", "premium"
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    period_days: Mapped[int]
    max_quality: Mapped[str] = mapped_column(String(10))  # e.g. "720p"
    has_ads: Mapped[bool]


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        enum_column(SubscriptionStatus, "subscription_status"),
        default=SubscriptionStatus.ACTIVE,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship()
    plan: Mapped[Plan] = relationship()


class Payment(CreatedAtMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Payments are kept for revenue reports, so a user with payments cannot be deleted.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    provider: Mapped[str] = mapped_column(String(50))  # e.g. "mock"
    scenario: Mapped[PaymentScenario] = mapped_column(
        enum_column(PaymentScenario, "payment_scenario")
    )
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()
    plan: Mapped[Plan] = relationship()
