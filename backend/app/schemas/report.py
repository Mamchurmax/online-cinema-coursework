"""Admin reports: the same JSON shape for every report."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Cell = str | int | float
MetricFormat = Literal["number", "money", "percent", "hours"]


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReportInfo(BaseModel):
    code: str
    title: str
    description: str


class PeriodRead(_FromAttributes):
    start: date
    end: date


class MetricRead(_FromAttributes):
    key: str
    label: str
    value: float
    format: MetricFormat


class SeriesRead(_FromAttributes):
    key: str
    label: str


class ChartRead(_FromAttributes):
    key: str
    title: str
    kind: Literal["bar", "hbar", "line", "pie"]
    x_key: str
    series: list[SeriesRead]
    data: list[dict[str, Cell]]


class ColumnRead(_FromAttributes):
    key: str
    label: str
    format: MetricFormat | Literal["text"]


class TableRead(_FromAttributes):
    title: str
    columns: list[ColumnRead]
    rows: list[dict[str, Cell]]


class ReportRead(_FromAttributes):
    code: str
    title: str
    period: PeriodRead
    generated_at: datetime
    metrics: list[MetricRead]
    charts: list[ChartRead]
    table: TableRead | None
    notes: list[str]
