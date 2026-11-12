"""Notifications: listeners turn events into messages; the bell API reads and marks them."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, NotificationType, User
from app.services.events.events import (
    PaymentFailed,
    PaymentSucceeded,
    SubscriptionActivated,
    SubscriptionExpiring,
)
from app.repositories.notification_repository import NotificationRepository
from app.services.events.bus import EventBus
from app.services.events.listeners import NotificationListener
from app.services.events.setup import build_event_bus
from app.services.notifications.notification_service import NotificationService


def register(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register",
                json={"email": email, "password": "notify-pass-1", "display_name": "N"})  # fmt: skip
    token = client.post("/api/v1/auth/login",
                        data={"username": email, "password": "notify-pass-1"}
                        ).json()["access_token"]  # fmt: skip
    return {"Authorization": f"Bearer {token}"}


def user_id(session: Session, email: str) -> int:
    return session.scalars(select(User.id).where(User.email == email)).one()


def test_billing_events_become_notifications(session: Session) -> None:
    user = User(email="n@example.com", password_hash="x", display_name="N")
    session.add(user)
    session.commit()
    # Only the notification observer: activation of a plan is tested in test_payments.py.
    listener = NotificationListener(NotificationService(NotificationRepository(session)))
    bus = EventBus()
    bus.subscribe(PaymentSucceeded, listener.on_payment_succeeded)
    bus.subscribe(PaymentFailed, listener.on_payment_failed)
    bus.subscribe(SubscriptionActivated, listener.on_subscription_activated)
    bus.subscribe(SubscriptionExpiring, listener.on_subscription_expiring)
    expires = datetime(2027, 1, 12, tzinfo=UTC)

    bus.publish(PaymentSucceeded(payment_id=1, user_id=user.id, plan_id=2, amount=Decimal("149")))
    bus.publish(PaymentFailed(payment_id=2, user_id=user.id, plan_id=2))
    bus.publish(SubscriptionActivated(subscription_id=1, user_id=user.id, plan_name="Premium",
                                      expires_at=expires))  # fmt: skip
    bus.publish(SubscriptionExpiring(subscription_id=1, user_id=user.id, plan_name="Premium",
                                     expires_at=expires, days_left=1))  # fmt: skip
    session.commit()

    rows = session.scalars(select(Notification).order_by(Notification.id)).all()
    assert [(n.type, n.message) for n in rows] == [
        (NotificationType.PAYMENT_SUCCEEDED, "Оплату 149.00 грн отримано. Дякуємо!"),
        (NotificationType.PAYMENT_FAILED,
         "Оплата не пройшла. Спробуйте ще раз або оберіть інший спосіб оплати."),
        (NotificationType.SUBSCRIPTION_ACTIVATED, "Підписку Premium активовано до 12.01.2027."),
        (NotificationType.SUBSCRIPTION_EXPIRING,
         "Підписка Premium закінчується завтра (12.01.2027). "
         "Продовжте її, щоб дивитися без реклами."),
    ]  # fmt: skip
    assert not any(n.is_read for n in rows)


def test_bell_api_lists_counts_and_marks_read(client: TestClient, session: Session) -> None:
    headers = register(client, "bell@example.com")
    other = register(client, "other@example.com")
    bus = build_event_bus(session)
    me = user_id(session, "bell@example.com")
    for payment_id in (1, 2, 3):
        bus.publish(PaymentFailed(payment_id=payment_id, user_id=me, plan_id=1))
    bus.publish(PaymentFailed(payment_id=9, user_id=user_id(session, "other@example.com"),
                              plan_id=1))  # fmt: skip
    session.commit()

    body = client.get("/api/v1/me/notifications", headers=headers).json()
    assert body["unread_count"] == 3 and len(body["items"]) == 3
    newest_id = body["items"][0]["id"]

    marked = client.post("/api/v1/me/notifications/read", json={"ids": [newest_id]},
                         headers=headers)  # fmt: skip
    assert marked.json() == {"unread_count": 2}
    unread = client.get("/api/v1/me/notifications", params={"unread_only": True},
                        headers=headers).json()  # fmt: skip
    assert newest_id not in [n["id"] for n in unread["items"]]

    assert client.post("/api/v1/me/notifications/read", json={},
                       headers=headers).json() == {"unread_count": 0}  # fmt: skip
    # Another user's notifications are neither visible nor marked.
    assert client.get("/api/v1/me/notifications", headers=other).json()["unread_count"] == 1


def test_cannot_mark_someone_elses_notification(client: TestClient, session: Session) -> None:
    alice = register(client, "alice@example.com")
    register(client, "bob@example.com")
    bus = build_event_bus(session)
    bus.publish(PaymentFailed(payment_id=1, user_id=user_id(session, "bob@example.com"),
                              plan_id=1))  # fmt: skip
    session.commit()
    bob_notification = session.scalars(select(Notification.id)).one()

    client.post("/api/v1/me/notifications/read", json={"ids": [bob_notification]}, headers=alice)

    session.expire_all()
    assert session.get(Notification, bob_notification).is_read is False


def test_notifications_require_login(client: TestClient) -> None:
    assert client.get("/api/v1/me/notifications").status_code == 401
