"""Pattern: Factory Method (GoF) — creating the payment provider.

- Creator:           `PaymentProviderFactory` — declares the factory method
                     `create_provider()` and uses its result in `provider()`.
- Concrete creator:  `MockPaymentProviderFactory` — creates `MockPaymentProvider`.
- Product:           `PaymentProvider` (providers.py) and its concrete products.

`PaymentService` works with whatever provider the factory returns, so a real
provider (e.g. LiqPay or Stripe) is added as one more product + creator and a line
in `FACTORIES`; the service, API and states stay unchanged. The provider is chosen
by the PAYMENT_PROVIDER setting.
"""

from abc import ABC, abstractmethod

from app.services.payments.providers import MockPaymentProvider, PaymentProvider


class UnknownPaymentProviderError(Exception):
    pass


class PaymentProviderFactory(ABC):
    """Creator."""

    def __init__(self) -> None:
        self._provider: PaymentProvider | None = None

    @abstractmethod
    def create_provider(self) -> PaymentProvider:
        """The factory method: subclasses decide which provider to build."""

    def provider(self) -> PaymentProvider:
        """The provider for this unit of work, created on first use."""
        if self._provider is None:
            self._provider = self.create_provider()
        return self._provider


class MockPaymentProviderFactory(PaymentProviderFactory):
    """Concrete creator for the demo provider."""

    def create_provider(self) -> PaymentProvider:
        return MockPaymentProvider()


FACTORIES: dict[str, type[PaymentProviderFactory]] = {
    MockPaymentProvider.code: MockPaymentProviderFactory,
}


def payment_provider_factory(name: str) -> PaymentProviderFactory:
    """Pick the creator configured in settings (PAYMENT_PROVIDER)."""
    try:
        return FACTORIES[name]()
    except KeyError:
        raise UnknownPaymentProviderError(f"Unknown payment provider '{name}'") from None
