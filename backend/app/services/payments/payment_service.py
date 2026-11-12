"""Paying for a plan: Factory Method picks the provider, State drives the status,
Observer (events) activates the subscription and notifies the user."""

from collections.abc import Sequence

from app.models import Payment, PaymentScenario, PaymentStatus, User
from app.repositories.billing_repository import PaymentRepository, PlanRepository
from app.services.events.bus import EventPublisher
from app.services.events.events import PaymentFailed, PaymentSucceeded
from app.services.payments.factory import PaymentProviderFactory
from app.services.payments.providers import ChargeResult
from app.services.payments.states import PaymentContext


class PlanNotPurchasableError(Exception):
    """Unknown plan, or a free one that cannot be bought."""


class PaymentNotFoundError(Exception):
    pass


class PaymentService:
    def __init__(
        self,
        payments: PaymentRepository,
        plans: PlanRepository,
        factory: PaymentProviderFactory,
        events: EventPublisher,
    ) -> None:
        self._payments = payments
        self._plans = plans
        self._provider = factory.provider()  # Factory Method: whichever provider is configured
        self._events = events

    def pay(self, user: User, plan_code: str, scenario: PaymentScenario) -> Payment:
        plan = self._plans.get_by_code(plan_code)
        if plan is None or plan.price <= 0:
            raise PlanNotPurchasableError(plan_code)

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            amount=plan.price,
            provider=self._provider.code,
            scenario=scenario,
            status=PaymentStatus.PENDING,
        )
        self._payments.add(payment)
        return self._apply(payment, self._provider.charge(payment))

    def simulate_bank_response(self, user: User, payment_id: int, approved: bool) -> Payment:
        """The "bank answered" button on the payment page (user's own payments only)."""
        payment = self._payments.get(payment_id)
        if payment is None or payment.user_id != user.id:
            raise PaymentNotFoundError(payment_id)
        return self._apply(payment, self._provider.bank_response(payment, approved))

    def resolve_by_admin(self, payment_id: int, approved: bool) -> Payment:
        """An administrator confirms or rejects a pending payment."""
        payment = self._payments.get(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)
        return self._apply(payment, self._provider.bank_response(payment, approved))

    def history(self, user: User) -> Sequence[Payment]:
        return self._payments.list_for_user(user.id)

    def pending(self) -> Sequence[Payment]:
        return self._payments.list_by_status(PaymentStatus.PENDING)

    def _apply(self, payment: Payment, result: ChargeResult) -> Payment:
        """Move the payment to its new state and tell the rest of the system.

        Everything (status, subscription, notifications) is committed together; an
        invalid transition raises before anything is saved.
        """
        context = PaymentContext(payment)
        try:
            if result is ChargeResult.SUCCEEDED:
                context.succeed()
                self._events.publish(
                    PaymentSucceeded(payment_id=payment.id, user_id=payment.user_id,
                                     plan_id=payment.plan_id, amount=payment.amount)
                )  # fmt: skip
            elif result is ChargeResult.FAILED:
                context.fail()
                self._events.publish(
                    PaymentFailed(payment_id=payment.id, user_id=payment.user_id,
                                  plan_id=payment.plan_id)
                )  # fmt: skip
            self._payments.commit()
        except Exception:
            self._payments.rollback()
            raise
        return payment
