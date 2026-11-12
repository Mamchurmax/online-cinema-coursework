"""Default plans, the current plan of a user, admin seeding."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import verify_password
from app.models import Plan, Subscription, SubscriptionStatus, User, UserRole
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.billing.plan_service import PlanNotConfiguredError, PlanService

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def plans(session: Session) -> PlanService:
    return PlanService(PlanRepository(session), SubscriptionRepository(session))


@pytest.fixture
def user(session: Session) -> User:
    user = User(email="viewer@example.com", password_hash="x", display_name="Viewer")
    session.add(user)
    session.commit()
    return user


def subscribe(session: Session, user: User, plan: Plan, **overrides) -> Subscription:
    values = {
        "status": SubscriptionStatus.ACTIVE,
        "started_at": NOW - timedelta(days=1),
        "expires_at": NOW + timedelta(days=29),
    } | overrides
    subscription = Subscription(user_id=user.id, plan_id=plan.id, **values)
    session.add(subscription)
    session.commit()
    return subscription


def test_default_plans_are_created_once(plans: PlanService) -> None:
    first = plans.ensure_default_plans()
    second = plans.ensure_default_plans()

    assert [(p.code, created) for p, created in first] == [("free", True), ("premium", True)]
    assert [created for _, created in second] == [False, False]
    free, premium = (p for p, _ in first)
    assert (free.price, free.max_quality, free.has_ads) == (Decimal("0.00"), "720p", True)
    assert (premium.price, premium.max_quality, premium.has_ads) == (
        Decimal("149.00"),
        "1080p",
        False,
    )


def test_existing_plan_keeps_admin_changes(plans: PlanService, session: Session) -> None:
    premium = dict(plans.ensure_default_plans())
    premium_plan = next(p for p in premium if p.code == "premium")
    premium_plan.price = Decimal("99.00")
    session.commit()

    plans.ensure_default_plans()

    assert PlanRepository(session).get_by_code("premium").price == Decimal("99.00")


def test_user_without_subscription_is_on_free(plans: PlanService, user: User) -> None:
    plans.ensure_default_plans()

    assert plans.current_plan(user.id, NOW).code == "free"


def test_active_subscription_gives_its_plan(
    plans: PlanService, session: Session, user: User
) -> None:
    plans.ensure_default_plans()
    subscribe(session, user, PlanRepository(session).get_by_code("premium"))

    assert plans.current_plan(user.id, NOW).code == "premium"


@pytest.mark.parametrize(
    "overrides",
    [
        {"expires_at": NOW - timedelta(seconds=1)},
        {"status": SubscriptionStatus.CANCELLED},
        {"started_at": NOW + timedelta(days=1), "expires_at": NOW + timedelta(days=31)},
    ],
)
def test_inactive_subscription_falls_back_to_free(
    plans: PlanService, session: Session, user: User, overrides: dict
) -> None:
    plans.ensure_default_plans()
    subscribe(session, user, PlanRepository(session).get_by_code("premium"), **overrides)

    assert plans.current_plan(user.id, NOW).code == "free"


def test_missing_free_plan_is_reported(plans: PlanService, user: User) -> None:
    with pytest.raises(PlanNotConfiguredError):
        plans.current_plan(user.id, NOW)


def test_ensure_admin_creates_then_promotes_and_rekeys(session: Session, user: User) -> None:
    auth = AuthService(UserRepository(session), Settings.instance())

    admin, created = auth.ensure_admin("Admin@Cinema.local", "admin-pass-1", "Admin")
    promoted, promoted_created = auth.ensure_admin("viewer@example.com", "new-pass-123", "V")

    assert created and admin.email == "admin@cinema.local" and admin.role is UserRole.ADMIN
    assert not promoted_created and promoted.id == user.id and promoted.role is UserRole.ADMIN
    assert verify_password("new-pass-123", promoted.password_hash)
