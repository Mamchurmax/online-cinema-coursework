"""User activity per day: registrations, active viewers, watch time
(concrete class of Template Method)."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from app.repositories.report_repository import UserInfo, WatchRow
from app.services.reports.base import BaseReport
from app.services.reports.result import (
    Chart,
    Column,
    Metric,
    ReportBody,
    ReportPeriod,
    Series,
    Table,
    day_of,
    hours,
)

TOP_USERS = 10


@dataclass
class ActivityRaw:
    watches: list[WatchRow]
    registrations: Sequence[datetime]
    users_total: int
    users: dict[int, UserInfo]


@dataclass
class DayStats:
    day: date
    new_users: int = 0
    active: set[int] = field(default_factory=set)
    watch_sec: int = 0


@dataclass
class UserStats:
    info: UserInfo
    titles: set[int] = field(default_factory=set)
    completions: int = 0
    watch_sec: int = 0


@dataclass
class ActivityData:
    days: list[DayStats]
    users: list[UserStats]  # most watch time first
    users_total: int
    new_users: int
    active_users: int
    completions: int
    watch_sec: int


class ActivityReport(BaseReport[ActivityRaw, ActivityData]):
    code = "activity"
    title = "Активність користувачів"
    description = "Реєстрації, активні глядачі та час перегляду по днях."

    def collect(self, period: ReportPeriod) -> ActivityRaw:
        watches = self._repository.watch_rows(period.start_at, period.end_at)
        return ActivityRaw(
            watches,
            self._repository.registrations(period.start_at, period.end_at),
            self._repository.count_users(period.end_at),
            self._repository.users({w.user_id for w in watches}),
        )

    def aggregate(self, raw: ActivityRaw, period: ReportPeriod) -> ActivityData:
        days = {day: DayStats(day) for day in period.days()}
        for moment in raw.registrations:
            if (stats := days.get(day_of(moment))) is not None:
                stats.new_users += 1

        users: dict[int, UserStats] = {}
        for watch in raw.watches:
            if (stats := days.get(day_of(watch.watched_at))) is not None:
                stats.active.add(watch.user_id)
                stats.watch_sec += watch.watched_sec
            info = raw.users.get(watch.user_id)
            if info is not None:
                user = users.setdefault(watch.user_id, UserStats(info))
                user.titles.add(watch.title_id)
                user.completions += watch.completed
                user.watch_sec += watch.watched_sec

        return ActivityData(
            days=list(days.values()),
            users=sorted(users.values(), key=lambda u: (-u.watch_sec, u.info.email)),
            users_total=raw.users_total,
            new_users=len(raw.registrations),
            active_users=len({w.user_id for w in raw.watches}),
            completions=sum(w.completed for w in raw.watches),
            watch_sec=sum(w.watched_sec for w in raw.watches),
        )

    def format(self, data: ActivityData, period: ReportPeriod) -> ReportBody:
        per_active = data.watch_sec / data.active_users if data.active_users else 0
        metrics = [
            Metric("users_total", "Усього користувачів", data.users_total),
            Metric("new_users", "Нових реєстрацій", data.new_users),
            Metric("active_users", "Активних глядачів", data.active_users),
            Metric("hours", "Годин перегляду", hours(data.watch_sec), "hours"),
            Metric("hours_per_user", "Годин на глядача", hours(per_active), "hours"),
            Metric("completions", "Переглянуто до кінця", data.completions),
        ]
        charts = [
            Chart(
                "daily_users", "Користувачі по днях", "line", "day",
                [Series("active", "Активні"), Series("new_users", "Нові")],
                [{"day": d.day.isoformat(), "active": len(d.active), "new_users": d.new_users}
                 for d in data.days],
            ),  # fmt: skip
            Chart(
                "daily_hours", "Години перегляду по днях", "bar", "day",
                [Series("hours", "Годин")],
                [{"day": d.day.isoformat(), "hours": hours(d.watch_sec)} for d in data.days],
            ),  # fmt: skip
        ]
        table = Table(
            "Найактивніші глядачі",
            [
                Column("user", "Користувач"),
                Column("email", "Email"),
                Column("titles", "Тайтлів", "number"),
                Column("completions", "До кінця", "number"),
                Column("hours", "Годин", "hours"),
            ],
            [
                {"user": u.info.display_name, "email": u.info.email, "titles": len(u.titles),
                 "completions": u.completions, "hours": hours(u.watch_sec)}
                for u in data.users[:TOP_USERS]
            ],  # fmt: skip
        )
        return ReportBody(metrics, charts, table)

    def notes(self, data: ActivityData) -> list[str]:
        return [
            "Історія переглядів зберігає останню позицію в кожному відео, тому день активності — "
            "це день останнього перегляду, а час перегляду — досягнута позиція.",
            "Дні рахуються за UTC.",
        ]
