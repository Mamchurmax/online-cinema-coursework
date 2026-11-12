from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import PaymentScenario, PaymentStatus, SubscriptionStatus


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    price: Decimal
    period_days: int
    max_quality: str
    has_ads: bool


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: SubscriptionStatus
    started_at: datetime
    expires_at: datetime
    plan: PlanRead


class MySubscription(BaseModel):
    """The plan the user has right now; `subscription` is null on Free."""

    plan: PlanRead
    subscription: SubscriptionRead | None


class PaymentCreate(BaseModel):
    plan_code: str
    scenario: PaymentScenario


class BankResponse(BaseModel):
    approved: bool


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    provider: str
    scenario: PaymentScenario
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime
    plan: PlanRead


class AdminPaymentRead(PaymentRead):
    user_email: str

    @classmethod
    def from_payment(cls, payment) -> "AdminPaymentRead":  # noqa: ANN001
        data = PaymentRead.model_validate(payment).model_dump()
        return cls(**data, user_email=payment.user.email)
