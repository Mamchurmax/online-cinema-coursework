"""Subscription plans and the plan a user currently has."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.models import Plan
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository

FREE_PLAN_CODE = "free"
PREMIUM_PLAN_CODE = "premium"


@dataclass(frozen=True)
class PlanSpec:
    code: str
    name: str
    price: Decimal
    period_days: int
    max_quality: str
    has_ads: bool


DEFAULT_PLANS = (
    PlanSpec(FREE_PLAN_CODE, "Free", Decimal("0.00"), 30, "720p", has_ads=True),
    PlanSpec(PREMIUM_PLAN_CODE, "Premium", Decimal("149.00"), 30, "1080p", has_ads=False),
)


class PlanNotConfiguredError(Exception):
    """The Free plan is missing: run `python -m scripts.seed`."""


class PlanService:
    def __init__(self, plans: PlanRepository, subscriptions: SubscriptionRepository) -> None:
        self._plans = plans
        self._subscriptions = subscriptions

    def ensure_default_plans(self) -> list[tuple[Plan, bool]]:
        """Create Free and Premium if missing. Existing plans keep admin edits."""
        result = []
        for spec in DEFAULT_PLANS:
            plan = self._plans.get_by_code(spec.code)
            created = plan is None
            if plan is None:
                plan = self._plans.save(
                    Plan(
                        code=spec.code,
                        name=spec.name,
                        price=spec.price,
                        period_days=spec.period_days,
                        max_quality=spec.max_quality,
                        has_ads=spec.has_ads,
                    )
                )
            result.append((plan, created))
        return result

    def current_plan(self, user_id: int, now: datetime | None = None) -> Plan:
        """Plan of the active subscription; without one every user is on Free."""
        subscription = self._subscriptions.get_active(user_id, now or datetime.now(UTC))
        if subscription is not None:
            return subscription.plan

        free = self._plans.get_by_code(FREE_PLAN_CODE)
        if free is None:
            raise PlanNotConfiguredError
        return free
