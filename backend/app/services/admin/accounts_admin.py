"""Admin: users and plans."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.models import Plan, User, UserRole
from app.repositories.billing_repository import PlanRepository
from app.repositories.user_repository import UserRepository
from app.services.admin.errors import AdminConflictError, AdminNotFoundError


@dataclass(frozen=True)
class PlanFields:
    name: str
    price: Decimal
    period_days: int
    max_quality: str
    has_ads: bool


class AccountsAdminService:
    def __init__(self, users: UserRepository, plans: PlanRepository) -> None:
        self._users = users
        self._plans = plans

    def search_users(
        self, query: str | None, page: int, page_size: int
    ) -> tuple[Sequence[User], int]:
        return self._users.search(query, (page - 1) * page_size, page_size)

    def set_role(self, actor: User, user_id: int, role: UserRole) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise AdminNotFoundError(f"User {user_id} not found")
        if user.id == actor.id and role is not UserRole.ADMIN:
            raise AdminConflictError("You cannot remove your own admin role")
        user.role = role
        return self._users.save(user)

    def delete_user(self, actor: User, user_id: int) -> None:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise AdminNotFoundError(f"User {user_id} not found")
        if user.id == actor.id:
            raise AdminConflictError("You cannot delete your own account here")
        if self._users.has_payments(user.id):
            # Payments are kept for the revenue report (see the Payment model).
            raise AdminConflictError("The user has payments and cannot be deleted")
        self._users.delete(user)

    def update_plan(self, plan_id: int, fields: PlanFields) -> Plan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise AdminNotFoundError(f"Plan {plan_id} not found")
        plan.name = fields.name.strip()
        plan.price = fields.price
        plan.period_days = fields.period_days
        plan.max_quality = fields.max_quality
        plan.has_ads = fields.has_ads
        return self._plans.save(plan)
