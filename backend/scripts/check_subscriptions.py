"""Daily job: remind about subscriptions ending in 3 days / 1 day and close ended ones.

    docker compose exec backend python -m scripts.check_subscriptions

Run it once a day (e.g. from cron / Windows Task Scheduler). Each reminder is a
SubscriptionExpiring event, which the NotificationListener turns into a notification.
"""

import sys

from app.core.db import SessionLocal
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.services.billing.subscription_service import SubscriptionService
from app.services.events.setup import build_event_bus


def main() -> int:
    with SessionLocal() as db:
        service = SubscriptionService(
            PlanRepository(db), SubscriptionRepository(db), build_event_bus(db)
        )
        reminders, expired = service.check_expiring()
    print(f"Reminders sent: {reminders}, subscriptions expired: {expired}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
