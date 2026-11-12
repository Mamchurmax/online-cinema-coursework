"""Pattern: State (GoF) — the life cycle of a payment.

- Context:         `PaymentContext` — wraps a `Payment` and delegates transitions to
                   its current state object.
- State:           `PaymentState` — declares the transitions `succeed()` and `fail()`.
- Concrete states: `PendingState`    — may become succeeded or failed;
                   `SucceededState`  — final: money received, cannot fail any more;
                   `FailedState`     — final: a new payment must be created.

Instead of `if payment.status == ...` scattered over the code, each state knows
which transitions are allowed. A forbidden one (e.g. failing a paid payment after
a late bank response) raises `InvalidPaymentTransitionError`.

    pending ──succeed()──> succeeded
       │
       └────fail()───────> failed
"""

from abc import ABC, abstractmethod

from app.models import Payment, PaymentStatus


class InvalidPaymentTransitionError(Exception):
    pass


class PaymentState(ABC):
    """State interface. By default every transition is forbidden."""

    status: PaymentStatus

    @property
    def is_final(self) -> bool:
        return False

    def succeed(self, context: "PaymentContext") -> None:
        raise InvalidPaymentTransitionError(f"Cannot succeed a {self.status.value} payment")

    def fail(self, context: "PaymentContext") -> None:
        raise InvalidPaymentTransitionError(f"Cannot fail a {self.status.value} payment")


class PendingState(PaymentState):
    status = PaymentStatus.PENDING

    def succeed(self, context: "PaymentContext") -> None:
        context.transition_to(SucceededState())

    def fail(self, context: "PaymentContext") -> None:
        context.transition_to(FailedState())


class SucceededState(PaymentState):
    status = PaymentStatus.SUCCEEDED

    @property
    def is_final(self) -> bool:
        return True


class FailedState(PaymentState):
    status = PaymentStatus.FAILED

    @property
    def is_final(self) -> bool:
        return True


_STATES: dict[PaymentStatus, type[PaymentState]] = {
    PaymentStatus.PENDING: PendingState,
    PaymentStatus.SUCCEEDED: SucceededState,
    PaymentStatus.FAILED: FailedState,
}


class PaymentContext:
    """Context: the payment plus its current state object."""

    def __init__(self, payment: Payment) -> None:
        self.payment = payment
        self._state = _STATES[payment.status or PaymentStatus.PENDING]()

    @property
    def state(self) -> PaymentState:
        return self._state

    def transition_to(self, state: PaymentState) -> None:
        self._state = state
        self.payment.status = state.status

    def succeed(self) -> None:
        self._state.succeed(self)

    def fail(self) -> None:
        self._state.fail(self)
