"""Plans, the current subscription and mock payments."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.config import Settings, get_settings
from app.repositories.billing_repository import (
    PaymentRepository,
    PlanRepository,
    SubscriptionRepository,
)
from app.schemas.billing import (
    AdminPaymentRead,
    BankResponse,
    MySubscription,
    PaymentCreate,
    PaymentRead,
    PlanRead,
)
from app.services.billing.plan_service import PlanService
from app.services.events.setup import build_event_bus
from app.services.payments.factory import payment_provider_factory
from app.services.payments.payment_service import (
    PaymentNotFoundError,
    PaymentService,
    PlanNotPurchasableError,
)
from app.services.payments.states import InvalidPaymentTransitionError

router = APIRouter(tags=["billing"])


def get_payment_service(
    db: DbSession, settings: Annotated[Settings, Depends(get_settings)]
) -> PaymentService:
    return PaymentService(
        PaymentRepository(db),
        PlanRepository(db),
        payment_provider_factory(settings.payment_provider),
        build_event_bus(db),
    )


def get_plan_service(db: DbSession) -> PlanService:
    return PlanService(PlanRepository(db), SubscriptionRepository(db))


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
PlanServiceDep = Annotated[PlanService, Depends(get_plan_service)]


def _payment_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, PaymentNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    if isinstance(exc, InvalidPaymentTransitionError):
        return HTTPException(status.HTTP_409_CONFLICT, "The payment is already completed")
    return HTTPException(status.HTTP_400_BAD_REQUEST, "This plan cannot be purchased")


@router.get("/plans", response_model=list[PlanRead])
def list_plans(plans: PlanServiceDep):
    """Public: plans for the pricing page."""
    return plans.all_plans()


@router.get("/me/subscription", response_model=MySubscription)
def my_subscription(user: CurrentUser, plans: PlanServiceDep):
    subscription = plans.current_subscription(user.id)
    plan = subscription.plan if subscription else plans.current_plan(user.id)
    return MySubscription(plan=plan, subscription=subscription)


@router.get("/me/payments", response_model=list[PaymentRead])
def my_payments(user: CurrentUser, payments: PaymentServiceDep):
    return payments.history(user)


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def pay(body: PaymentCreate, user: CurrentUser, payments: PaymentServiceDep):
    """Mock checkout: `scenario` decides the outcome (success / pending / failed)."""
    try:
        return payments.pay(user, body.plan_code, body.scenario)
    except PlanNotPurchasableError as exc:
        raise _payment_errors(exc) from None


@router.post("/payments/{payment_id}/bank-response", response_model=PaymentRead)
def simulate_bank_response(
    payment_id: int, body: BankResponse, user: CurrentUser, payments: PaymentServiceDep
):
    """The "simulate bank response" button for a pending payment."""
    try:
        return payments.simulate_bank_response(user, payment_id, body.approved)
    except (PaymentNotFoundError, InvalidPaymentTransitionError) as exc:
        raise _payment_errors(exc) from None


@router.get("/admin/payments/pending", response_model=list[AdminPaymentRead])
def pending_payments(_: AdminUser, payments: PaymentServiceDep):
    return [AdminPaymentRead.from_payment(p) for p in payments.pending()]


@router.post("/admin/payments/{payment_id}/resolve", response_model=PaymentRead)
def resolve_payment(
    payment_id: int, body: BankResponse, _: AdminUser, payments: PaymentServiceDep
):
    """An administrator approves or rejects a pending payment."""
    try:
        return payments.resolve_by_admin(payment_id, body.approved)
    except (PaymentNotFoundError, InvalidPaymentTransitionError) as exc:
        raise _payment_errors(exc) from None
