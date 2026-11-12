"""Subscription revenue (concrete class of Template Method)."""

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models import PaymentStatus
from app.repositories.report_repository import PaymentRow
from app.services.reports.base import BaseReport
from app.services.reports.result import (
    Chart,
    Column,
    Metric,
    ReportBody,
    ReportPeriod,
    Series,
    Table,
)

STATUS_LABELS = {
    PaymentStatus.SUCCEEDED: "Успішні",
    PaymentStatus.PENDING: "Очікують",
    PaymentStatus.FAILED: "Відхилені",
}


@dataclass
class RevenueRaw:
    payments: list[PaymentRow]
    active_subscriptions: dict[str, int]  # plan name -> count


@dataclass
class PlanRevenue:
    name: str
    payments: int
    revenue: Decimal


@dataclass
class RevenueData:
    daily: dict[date, Decimal]  # per day or per month, see ReportPeriod.by_month
    plans: list[PlanRevenue]  # biggest revenue first
    statuses: Counter[PaymentStatus]
    revenue: Decimal
    paying_users: int
    active_subscriptions: dict[str, int]


def money(value: Decimal) -> float:
    return float(round(value, 2))


class RevenueReport(BaseReport[RevenueRaw, RevenueData]):
    code = "revenue"
    title = "Дохід від підписок"
    description = "Успішні оплати по днях і тарифах, статуси платежів."

    def collect(self, period: ReportPeriod) -> RevenueRaw:
        # Active subscriptions are counted at the end of the period (or now, if earlier).
        snapshot = min(self._clock(), period.end_at)
        return RevenueRaw(
            self._repository.payments(period.start_at, period.end_at),
            self._repository.active_subscriptions_by_plan(snapshot),
        )

    def aggregate(self, raw: RevenueRaw, period: ReportPeriod) -> RevenueData:
        daily = {bucket: Decimal(0) for bucket in period.buckets()}
        plans: dict[str, PlanRevenue] = {}
        statuses: Counter[PaymentStatus] = Counter()
        paying: set[int] = set()
        for payment in raw.payments:
            statuses[payment.status] += 1
            if payment.status is not PaymentStatus.SUCCEEDED:
                continue
            if (bucket := period.bucket_of(payment.created_at)) is not None:
                daily[bucket] += payment.amount
            plan = plans.setdefault(payment.plan_code, PlanRevenue(payment.plan_name, 0, Decimal(0)))
            plan.payments += 1
            plan.revenue += payment.amount
            paying.add(payment.user_id)

        return RevenueData(
            daily=daily,
            plans=sorted(plans.values(), key=lambda p: (-p.revenue, p.name)),
            statuses=statuses,
            revenue=sum((p.revenue for p in plans.values()), Decimal(0)),
            paying_users=len(paying),
            active_subscriptions=raw.active_subscriptions,
        )

    def format(self, data: RevenueData, period: ReportPeriod) -> ReportBody:
        finished = data.statuses[PaymentStatus.SUCCEEDED] + data.statuses[PaymentStatus.FAILED]
        success_rate = data.statuses[PaymentStatus.SUCCEEDED] / finished * 100 if finished else 0
        per_user = data.revenue / data.paying_users if data.paying_users else Decimal(0)
        metrics = [
            Metric("revenue", "Дохід", money(data.revenue), "money"),
            Metric("payments", "Успішних оплат", data.statuses[PaymentStatus.SUCCEEDED]),
            Metric("paying_users", "Платників", data.paying_users),
            Metric("arppu", "Дохід на платника", money(per_user), "money"),
            Metric("success_rate", "Успішність оплат", round(success_rate, 1), "percent"),
            Metric("active_subscriptions", "Активних підписок",
                   sum(data.active_subscriptions.values())),  # fmt: skip
        ]
        charts = [
            Chart(
                "daily_revenue", f"Дохід по {period.bucket_name}", "bar", "day",
                [Series("revenue", "Дохід, грн")],
                [{"day": period.label(d), "revenue": money(v)} for d, v in data.daily.items()],
            ),  # fmt: skip
            Chart(
                "by_plan", "Дохід за тарифами", "pie", "plan", [Series("revenue", "Дохід, грн")],
                [{"plan": p.name, "revenue": money(p.revenue)} for p in data.plans],
            ),  # fmt: skip
            Chart(
                "statuses", "Статуси платежів", "bar", "status", [Series("count", "Платежів")],
                [{"status": label, "count": data.statuses[s]}
                 for s, label in STATUS_LABELS.items()],
            ),  # fmt: skip
        ]
        total = data.revenue or Decimal(1)
        table = Table(
            "Дохід за тарифами",
            [
                Column("plan", "Тариф"),
                Column("payments", "Оплат", "number"),
                Column("revenue", "Дохід", "money"),
                Column("share", "Частка", "percent"),
                Column("active", "Активних підписок", "number"),
            ],
            [
                {"plan": p.name, "payments": p.payments, "revenue": money(p.revenue),
                 "share": round(float(p.revenue / total * 100), 1),
                 "active": data.active_subscriptions.get(p.name, 0)}
                for p in data.plans
            ],  # fmt: skip
        )
        return ReportBody(metrics, charts, table)

    def notes(self, data: RevenueData) -> list[str]:
        notes = ["Дохід — сума успішних оплат, створених за період (дні за UTC)."]
        if data.statuses[PaymentStatus.PENDING]:
            notes.append(
                f"{data.statuses[PaymentStatus.PENDING]} платеж(ів) ще очікують відповіді банку "
                "й у дохід не входять."
            )
        return notes
