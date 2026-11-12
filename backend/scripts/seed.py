"""Create required reference data: Free/Premium plans and an administrator.

    docker compose exec backend python -m scripts.seed
    docker compose exec backend python -m scripts.seed --admin-email admin@cinema.local

The admin password is taken from --admin-password or the ADMIN_PASSWORD
environment variable; without one, no admin is created. Re-running is safe.
"""

import argparse
import os
import sys

from app.core.config import Settings
from app.core.db import SessionLocal
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.billing.plan_service import PlanService

MIN_PASSWORD_LENGTH = 8


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed plans and an admin user")
    parser.add_argument(
        "--admin-email", default=os.environ.get("ADMIN_EMAIL", "admin@cinema.local")
    )
    parser.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", ""))
    parser.add_argument("--admin-name", default="Адміністратор")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    with SessionLocal() as db:
        plans = PlanService(PlanRepository(db), SubscriptionRepository(db))
        for plan, created in plans.ensure_default_plans():
            state = "created" if created else "exists "
            ads = "with ads" if plan.has_ads else "no ads"
            print(f"plan {state} {plan.code}: {plan.price} / {plan.period_days} days, "
                  f"up to {plan.max_quality}, {ads}")  # fmt: skip

        if not args.admin_password:
            print("admin skipped: pass --admin-password or set ADMIN_PASSWORD")
            return 0
        if len(args.admin_password) < MIN_PASSWORD_LENGTH:
            print(f"Error: admin password must be at least {MIN_PASSWORD_LENGTH} characters")
            return 1

        auth = AuthService(UserRepository(db), Settings.instance())
        admin, created = auth.ensure_admin(args.admin_email, args.admin_password, args.admin_name)
        print(f"admin {'created' if created else 'updated'}: {admin.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
