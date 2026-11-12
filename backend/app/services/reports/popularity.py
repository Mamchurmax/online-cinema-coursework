"""Most popular titles and genres for a period (concrete class of Template Method)."""

from collections import Counter
from dataclasses import dataclass, field

from app.models import TitleType
from app.repositories.report_repository import TitleInfo, WatchRow
from app.services.reports.base import BaseReport
from app.services.reports.result import (
    Chart,
    Column,
    Metric,
    ReportBody,
    ReportPeriod,
    Series,
    Table,
    hours,
)

TOP_TITLES = 10
TOP_GENRES = 10
TYPE_LABELS = {TitleType.MOVIE: "Фільми", TitleType.SERIES: "Серіали"}


@dataclass
class PopularityRaw:
    watches: list[WatchRow]
    titles: dict[int, TitleInfo]
    genres: dict[int, list[str]]


@dataclass
class TitleStats:
    info: TitleInfo
    viewers: set[int] = field(default_factory=set)
    completions: int = 0
    watch_sec: int = 0

    @property
    def views(self) -> int:
        return len(self.viewers)


@dataclass
class PopularityData:
    titles: list[TitleStats]  # most viewed first
    genre_views: Counter[str]
    type_views: Counter[TitleType]
    unique_viewers: int


class PopularityReport(BaseReport[PopularityRaw, PopularityData]):
    code = "popularity"
    title = "Популярні фільми та жанри"
    description = "Які тайтли й жанри дивилися найбільше за період."

    def collect(self, period: ReportPeriod) -> PopularityRaw:
        watches = self._repository.watch_rows(period.start_at, period.end_at)
        title_ids = {w.title_id for w in watches}
        return PopularityRaw(
            watches, self._repository.titles(title_ids), self._repository.genres_of(title_ids)
        )

    def aggregate(self, raw: PopularityRaw, period: ReportPeriod) -> PopularityData:
        stats: dict[int, TitleStats] = {}
        for watch in raw.watches:
            info = raw.titles.get(watch.title_id)
            if info is None:
                continue
            item = stats.setdefault(watch.title_id, TitleStats(info))
            item.viewers.add(watch.user_id)
            item.completions += watch.completed
            item.watch_sec += watch.progress_sec

        genre_views: Counter[str] = Counter()
        type_views: Counter[TitleType] = Counter()
        for title_id, item in stats.items():
            type_views[item.info.type] += item.views
            for genre in raw.genres.get(title_id, []):
                genre_views[genre] += item.views

        ranked = sorted(
            stats.values(), key=lambda s: (-s.views, -s.completions, -s.watch_sec, s.info.title)
        )
        viewers = {w.user_id for w in raw.watches if w.title_id in stats}
        return PopularityData(ranked, genre_views, type_views, len(viewers))

    def format(self, data: PopularityData, period: ReportPeriod) -> ReportBody:
        top = data.titles[:TOP_TITLES]
        metrics = [
            Metric("views", "Переглядів", sum(s.views for s in data.titles)),
            Metric("viewers", "Глядачів", data.unique_viewers),
            Metric("completions", "Переглянуто до кінця", sum(s.completions for s in data.titles)),
            Metric("titles", "Різних тайтлів", len(data.titles)),
            Metric("hours", "Годин перегляду", hours(sum(s.watch_sec for s in data.titles)),
                   "hours"),  # fmt: skip
        ]
        charts = [
            Chart(
                "top_titles", "Топ тайтлів", "hbar", "title",
                [Series("views", "Переглядів"), Series("completions", "До кінця")],
                [{"title": s.info.title, "views": s.views, "completions": s.completions}
                 for s in top],
            ),  # fmt: skip
            Chart(
                "top_genres", "Популярні жанри", "bar", "genre", [Series("views", "Переглядів")],
                [{"genre": g, "views": v}
                 for g, v in sorted(data.genre_views.items(), key=lambda gv: (-gv[1], gv[0]))
                 [:TOP_GENRES]],
            ),  # fmt: skip
            Chart(
                "by_type", "Фільми та серіали", "pie", "type", [Series("views", "Переглядів")],
                [{"type": TYPE_LABELS[t], "views": data.type_views[t]}
                 for t in TitleType if data.type_views[t]],
            ),  # fmt: skip
        ]
        table = Table(
            "Рейтинг тайтлів",
            [
                Column("rank", "№", "number"),
                Column("title", "Назва"),
                Column("type", "Тип"),
                Column("views", "Переглядів", "number"),
                Column("completions", "До кінця", "number"),
                Column("hours", "Годин", "hours"),
            ],
            [
                {"rank": i, "title": s.info.title, "type": TYPE_LABELS[s.info.type],
                 "views": s.views, "completions": s.completions, "hours": hours(s.watch_sec)}
                for i, s in enumerate(top, start=1)
            ],  # fmt: skip
        )
        return ReportBody(metrics, charts, table)

    def notes(self, data: PopularityData) -> list[str]:
        return [
            "Перегляд — користувач, який відкрив тайтл за період (епізоди рахуються як серіал).",
            "Жанр отримує перегляди всіх своїх тайтлів, тому сума за жанрами більша.",
        ]
