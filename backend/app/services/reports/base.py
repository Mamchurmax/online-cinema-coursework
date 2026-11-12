"""Pattern: Template Method (GoF) — every report is built in the same three steps.

- Abstract class:   `BaseReport` — `build(period)` is the template method; it fixes the
                    algorithm `collect → aggregate → format` and wraps the outcome into
                    a `ReportResult` (code, title, period, time of generation, notes).
- Primitive steps (abstract, every report implements them):
    `collect(period)`         — fetch raw rows for the period from `ReportRepository`;
    `aggregate(raw, period)`  — group and count them (per day, title, genre, plan...);
    `format(data, period)`    — turn the numbers into metrics, charts and a table.
- Hook (optional):  `notes(data)` — remarks shown under the report; empty by default.
- Concrete classes: `PopularityReport`, `ActivityReport`, `RevenueReport`.

The order of the steps and the shape of the result never change, so the API and the
admin UI work with any report; a new report only fills in the three steps.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar, final

from app.repositories.report_repository import ReportRepository
from app.services.reports.result import ReportBody, ReportPeriod, ReportResult


class BaseReport[RawT, DataT](ABC):
    """Abstract class of the Template Method pattern."""

    code: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]

    def __init__(
        self,
        repository: ReportRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._clock = clock

    @final
    def build(self, period: ReportPeriod) -> ReportResult:
        """The template method: subclasses change the steps, never their order."""
        raw = self.collect(period)
        data = self.aggregate(raw, period)
        body = self.format(data, period)
        return ReportResult(
            code=self.code,
            title=self.title,
            period=period,
            generated_at=self._clock(),
            metrics=body.metrics,
            charts=body.charts,
            table=body.table,
            notes=self.notes(data),
        )

    @abstractmethod
    def collect(self, period: ReportPeriod) -> RawT:
        """Step 1: raw rows from the database."""

    @abstractmethod
    def aggregate(self, raw: RawT, period: ReportPeriod) -> DataT:
        """Step 2: grouped numbers."""

    @abstractmethod
    def format(self, data: DataT, period: ReportPeriod) -> ReportBody:
        """Step 3: metrics, charts and a table for the UI."""

    def notes(self, data: DataT) -> list[str]:
        """Hook: remarks about how the numbers were obtained."""
        return []
