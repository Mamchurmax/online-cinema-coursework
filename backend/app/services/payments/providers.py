"""Payment providers — the products created by `PaymentProviderFactory` (factory.py)."""

from abc import ABC, abstractmethod
from enum import StrEnum

from app.models import Payment, PaymentScenario


class ChargeResult(StrEnum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"  # the bank has not answered yet
    FAILED = "failed"


class PaymentProvider(ABC):
    """Product: talks to a payment system."""

    code: str

    @abstractmethod
    def charge(self, payment: Payment) -> ChargeResult:
        """Start charging the user for the payment."""

    @abstractmethod
    def bank_response(self, payment: Payment, approved: bool) -> ChargeResult:
        """The final answer of the bank for a pending payment."""


class MockPaymentProvider(PaymentProvider):
    """Concrete product: no real money; the user picks the outcome (`payment.scenario`)."""

    code = "mock"

    _RESULTS = {
        PaymentScenario.SUCCESS: ChargeResult.SUCCEEDED,
        PaymentScenario.PENDING: ChargeResult.PENDING,
        PaymentScenario.FAILED: ChargeResult.FAILED,
    }

    def charge(self, payment: Payment) -> ChargeResult:
        return self._RESULTS[payment.scenario]

    def bank_response(self, payment: Payment, approved: bool) -> ChargeResult:
        return ChargeResult.SUCCEEDED if approved else ChargeResult.FAILED
