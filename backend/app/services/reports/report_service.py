"""Picks a report by its code, checks the period and runs the template method."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from app.repositories.report_repository import ReportRepository
from app.services.reports.activity import ActivityReport
from app.services.reports.base import BaseReport
from app.services.reports.popularity import PopularityReport
from app.services.reports.result import ReportPeriod, ReportResult
from app.services.reports.revenue import RevenueReport

REPORTS: tuple[type[BaseReport], ...] = (PopularityReport, ActivityReport, RevenueReport)
DEFAULT_DAYS = 30
MAX_DAYS = 366


class UnknownReportError(Exception):
    """There is no report with this code."""


class InvalidPeriodError(Exception):
    """The dates are reversed or the period is too long."""


class ReportService:
    def __init__(
        self,
        repository: ReportRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._reports = {report.code: report for report in REPORTS}

    def available(self) -> list[type[BaseReport]]:
        return list(self._reports.values())

    def period(self, date_from: date | None, date_to: date | None) -> ReportPeriod:
        """Defaults: the last 30 days up to today (UTC)."""
        end = date_to or self._clock().astimezone(UTC).date()
        start = date_from or end - timedelta(days=DEFAULT_DAYS - 1)
        if start > end:
            raise InvalidPeriodError("date_from must not be later than date_to")
        if (end - start).days + 1 > MAX_DAYS:
            raise InvalidPeriodError(f"The period must not exceed {MAX_DAYS} days")
        return ReportPeriod(start, end)

    def build(
        self, code: str, date_from: date | None = None, date_to: date | None = None
    ) -> ReportResult:
        report_cls = self._reports.get(code)
        if report_cls is None:
            raise UnknownReportError(f"Unknown report: {code}")
        report = report_cls(self._repository, self._clock)
        return report.build(self.period(date_from, date_to))
