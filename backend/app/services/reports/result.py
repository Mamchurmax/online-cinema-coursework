"""What every report returns: a period, key metrics, charts and a table.

The structure is the same for all reports, so the admin UI renders any of them with
one component (Recharts for charts).
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

type Cell = str | int | float
type MetricFormat = Literal["number", "money", "percent", "hours"]
type ChartKind = Literal["bar", "hbar", "line", "pie"]


@dataclass(frozen=True)
class ReportPeriod:
    """Calendar days from `start` to `end`, both inclusive (UTC)."""

    start: date
    end: date

    @property
    def start_at(self) -> datetime:
        return datetime.combine(self.start, time.min, UTC)

    @property
    def end_at(self) -> datetime:
        """Exclusive upper bound: midnight after the last day."""
        return datetime.combine(self.end + timedelta(days=1), time.min, UTC)

    def days(self) -> list[date]:
        return [self.start + timedelta(days=i) for i in range((self.end - self.start).days + 1)]


def day_of(moment: datetime) -> date:
    """UTC calendar day; SQLite returns naive datetimes that are already UTC."""
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(UTC).date()


def hours(seconds: float) -> float:
    return round(seconds / 3600, 1)


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    value: float
    format: MetricFormat = "number"


@dataclass(frozen=True)
class Series:
    key: str  # column in Chart.data
    label: str


@dataclass(frozen=True)
class Chart:
    key: str
    title: str
    kind: ChartKind
    x_key: str  # category / day column in `data`
    series: list[Series]
    data: list[dict[str, Cell]]


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    format: MetricFormat | Literal["text"] = "text"


@dataclass(frozen=True)
class Table:
    title: str
    columns: list[Column]
    rows: list[dict[str, Cell]]


@dataclass(frozen=True)
class ReportBody:
    """The part a concrete report produces in its `format` step."""

    metrics: list[Metric]
    charts: list[Chart]
    table: Table | None = None


@dataclass(frozen=True)
class ReportResult:
    code: str
    title: str
    period: ReportPeriod
    generated_at: datetime
    metrics: list[Metric]
    charts: list[Chart]
    table: Table | None
    notes: list[str] = field(default_factory=list)
