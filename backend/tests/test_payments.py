"""Payments (Factory Method + State), subscription activation (Observer) and expiry."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Notification,
    NotificationType,
    Payment,
    PaymentScenario,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    Title,
    TitleType,
    User,
    UserRole,
    VideoAsset,
)
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.services.billing.plan_service import PlanService
from app.services.billing.subscription_service import SubscriptionService
from app.services.events.setup import build_event_bus
from app.services.payments.factory import (
    MockPaymentProviderFactory,
    UnknownPaymentProviderError,
    payment_provider_factory,
)
from app.services.payments.providers import ChargeResult, MockPaymentProvider
from app.services.payments.states import (
    FailedState,
    InvalidPaymentTransitionError,
    PaymentContext,
    PendingState,
    SucceededState,
)

# --- State ---------------------------------------------------------------------


def payment(status: PaymentStatus = PaymentStatus.PENDING) -> Payment:
    return Payment(status=status, scenario=PaymentScenario.PENDING, amount=Decimal(1))


def test_pending_payment_can_succeed_or_fail() -> None:
    paid, declined = PaymentContext(payment()), PaymentContext(payment())

    paid.succeed()
    declined.fail()

    assert isinstance(paid.state, SucceededState) and paid.payment.status is PaymentStatus.SUCCEEDED
    assert isinstance(declined.state, FailedState) and declined.payment.status is PaymentStatus.FAILED
    assert paid.state.is_final and declined.state.is_final
    assert not PendingState().is_final


@pytest.mark.parametrize("status", [PaymentStatus.SUCCEEDED, PaymentStatus.FAILED])
@pytest.mark.parametrize("transition", ["succeed", "fail"])
def test_final_states_reject_every_transition(status: PaymentStatus, transition: str) -> None:
    context = PaymentContext(payment(status))

    with pytest.raises(InvalidPaymentTransitionError):
        getattr(context, transition)()
    assert context.payment.status is status


# --- Factory Method --------------------------------------------------------------


def test_factory_creates_the_configured_provider_once() -> None:
    factory = payment_provider_factory("mock")

    assert isinstance(factory, MockPaymentProviderFactory)
    assert isinstance(factory.provider(), MockPaymentProvider)
    assert factory.provider() is factory.provider()


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(UnknownPaymentProviderError):
        payment_provider_factory("paypal")


@pytest.mark.parametrize(
    ("scenario", "result"),
    [
        (PaymentScenario.SUCCESS, ChargeResult.SUCCEEDED),
        (PaymentScenario.PENDING, ChargeResult.PENDING),
        (PaymentScenario.FAILED, ChargeResult.FAILED),
    ],
)
def test_mock_provider_follows_the_chosen_scenario(scenario, result) -> None:  # noqa: ANN001
    provider = MockPaymentProvider()

    assert provider.charge(Payment(scenario=scenario)) is result
    assert provider.bank_response(Payment(scenario=scenario), approved=True) is ChargeResult.SUCCEEDED
    assert provider.bank_response(Payment(scenario=scenario), approved=False) is ChargeResult.FAILED


# --- API: the whole chain ------------------------------------------------------


@pytest.fixture
def plans(session: Session) -> None:
    PlanService(PlanRepository(session), SubscriptionRepository(session)).ensure_default_plans()


def login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register",
                json={"email": email, "password": "payer-pass-1", "display_name": "P"})  # fmt: skip
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "payer-pass-1"}
                        ).json()["access_token"]  # fmt: skip
    return {"Authorization": f"Bearer {token}"}


def pay(client: TestClient, headers: dict, scenario: str, plan: str = "premium"):
    return client.post("/api/v1/payments", json={"plan_code": plan, "scenario": scenario},
                       headers=headers)  # fmt: skip


def notification_types(session: Session, email: str) -> list[NotificationType]:
    user_id = session.scalars(select(User.id).where(User.email == email)).one()
    rows = session.scalars(select(Notification).where(Notification.user_id == user_id)
                           .order_by(Notification.id))  # fmt: skip
    return [n.type for n in rows]


def test_successful_payment_activates_premium_and_notifies(
    client: TestClient, session: Session, plans: None
) -> None:
    headers = login(client, "rich@example.com")

    response = pay(client, headers, "success")
    me = client.get("/api/v1/me/subscription", headers=headers).json()

    assert response.status_code == 201
    assert response.json()["status"] == "succeeded"
    assert response.json()["amount"] == "149.00"
    assert me["plan"]["code"] == "premium" and me["subscription"]["status"] == "active"
    assert notification_types(session, "rich@example.com") == [
        NotificationType.SUBSCRIPTION_ACTIVATED,
        NotificationType.PAYMENT_SUCCEEDED,
    ]


def test_failed_payment_keeps_free_and_notifies(
    client: TestClient, session: Session, plans: None
) -> None:
    headers = login(client, "poor@example.com")

    response = pay(client, headers, "failed")
    me = client.get("/api/v1/me/subscription", headers=headers).json()

    assert response.json()["status"] == "failed"
    assert (me["plan"]["code"], me["subscription"]) == ("free", None)
    assert notification_types(session, "poor@example.com") == [NotificationType.PAYMENT_FAILED]


def test_pending_payment_waits_for_the_bank(
    client: TestClient, session: Session, plans: None
) -> None:
    headers = login(client, "wait@example.com")

    pending = pay(client, headers, "pending").json()
    assert pending["status"] == "pending"
    assert client.get("/api/v1/me/subscription", headers=headers).json()["subscription"] is None
    assert notification_types(session, "wait@example.com") == []

    approved = client.post(f"/api/v1/payments/{pending['id']}/bank-response",
                           json={"approved": True}, headers=headers)  # fmt: skip
    assert approved.json()["status"] == "succeeded"
    assert client.get("/api/v1/me/subscription", headers=headers).json()["plan"]["code"] == "premium"

    again = client.post(f"/api/v1/payments/{pending['id']}/bank-response",
                        json={"approved": False}, headers=headers)  # fmt: skip
    assert again.status_code == 409  # State: a succeeded payment cannot fail any more


def test_paying_again_extends_the_subscription(
    client: TestClient, session: Session, plans: None
) -> None:
    headers = login(client, "loyal@example.com")
    pay(client, headers, "success")
    first_end = datetime.fromisoformat(
        client.get("/api/v1/me/subscription", headers=headers).json()["subscription"]["expires_at"]
    )

    pay(client, headers, "success")
    me = client.get("/api/v1/me/subscription", headers=headers).json()

    assert datetime.fromisoformat(me["subscription"]["expires_at"]) - first_end == timedelta(days=30)
    assert session.scalars(select(Subscription)).all().__len__() == 1


def test_payment_validation_and_ownership(client: TestClient, plans: None) -> None:
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    bobs_pending = pay(client, bob, "pending").json()

    assert pay(client, alice, "success", plan="free").status_code == 400
    assert pay(client, alice, "success", plan="gold").status_code == 400
    assert pay(client, alice, "bitcoin").status_code == 422
    assert client.post(f"/api/v1/payments/{bobs_pending['id']}/bank-response",
                       json={"approved": True}, headers=alice).status_code == 404  # fmt: skip
    assert client.post("/api/v1/payments", json={"plan_code": "premium", "scenario": "success"}
                       ).status_code == 401  # fmt: skip
    assert [p["id"] for p in client.get("/api/v1/me/payments", headers=alice).json()] == []


def test_admin_resolves_pending_payments(
    client: TestClient, session: Session, plans: None
) -> None:
    user = login(client, "user@example.com")
    admin = login(client, "admin@example.com")
    admin_user = session.scalars(select(User).where(User.email == "admin@example.com")).one()
    admin_user.role = UserRole.ADMIN
    session.commit()
    pending = pay(client, user, "pending").json()

    assert client.get("/api/v1/admin/payments/pending", headers=user).status_code == 403
    queue = client.get("/api/v1/admin/payments/pending", headers=admin).json()
    assert [(p["id"], p["user_email"]) for p in queue] == [(pending["id"], "user@example.com")]

    rejected = client.post(f"/api/v1/admin/payments/{pending['id']}/resolve",
                           json={"approved": False}, headers=admin)  # fmt: skip
    assert rejected.json()["status"] == "failed"
    assert client.get("/api/v1/admin/payments/pending", headers=admin).json() == []


def test_premium_after_payment_unlocks_1080p_without_ads(
    client: TestClient, session: Session, plans: None
) -> None:
    movie = Title(type=TitleType.MOVIE, title="Сінтел")
    session.add(movie)
    session.flush()
    session.add(VideoAsset(title_id=movie.id, hls_path="s/master.m3u8",
                           qualities=["360p", "720p", "1080p"], duration_sec=888))  # fmt: skip
    session.commit()
    headers = login(client, "upgrade@example.com")

    before = client.get(f"/api/v1/playback/titles/{movie.id}", headers=headers).json()
    pay(client, headers, "success")
    after = client.get(f"/api/v1/playback/titles/{movie.id}", headers=headers).json()

    assert (before["plan_code"], before["locked_qualities"]) == ("free", ["1080p"])
    assert (after["plan_code"], after["locked_qualities"], after["ad"]) == ("premium", [], None)


# --- Expiry job ----------------------------------------------------------------


def test_daily_check_reminds_and_expires(session: Session, plans: None) -> None:
    now = datetime(2026, 12, 10, 9, 0, tzinfo=UTC)
    premium = PlanRepository(session).get_by_code("premium")
    users = [User(email=f"u{i}@example.com", password_hash="x", display_name="U") for i in range(4)]
    session.add_all(users)
    session.flush()
    for user, ends_in in zip(users, [timedelta(days=3), timedelta(hours=20), timedelta(days=10),
                                     -timedelta(hours=1)], strict=True):  # fmt: skip
        session.add(Subscription(user_id=user.id, plan_id=premium.id,
                                 status=SubscriptionStatus.ACTIVE, started_at=now - timedelta(days=20),
                                 expires_at=now + ends_in))  # fmt: skip
    session.commit()

    service = SubscriptionService(PlanRepository(session), SubscriptionRepository(session),
                                  build_event_bus(session), clock=lambda: now)  # fmt: skip
    reminders, expired = service.check_expiring()

    assert (reminders, expired) == (2, 1)
    messages = sorted(m.split(" (")[0] for m in session.scalars(select(Notification.message)))
    assert messages == [
        "Підписка Premium закінчується завтра",
        "Підписка Premium закінчується через 3 дн.",
    ]
    statuses = {s.user_id: s.status for s in session.scalars(select(Subscription))}
    assert statuses[users[3].id] is SubscriptionStatus.EXPIRED
