"""Admin reports: the template method, the three reports and the API."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Episode,
    Genre,
    Payment,
    PaymentScenario,
    PaymentStatus,
    Plan,
    Season,
    Subscription,
    Title,
    TitleType,
    User,
    UserRole,
    VideoAsset,
    WatchHistory,
)
from app.repositories.report_repository import ReportRepository
from app.services.reports.base import BaseReport
from app.services.reports.report_service import (
    REPORTS,
    InvalidPeriodError,
    ReportService,
    UnknownReportError,
)
from app.services.reports.result import Metric, ReportBody, ReportPeriod, ReportResult, hours

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
WEEK = (date(2026, 11, 1), date(2026, 11, 7))


def at(day: int, hour: int = 12, month: int = 11) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=UTC)


@pytest.fixture
def world(session: Session) -> dict:
    """Three viewers, two movies and a series watched during 1–7 Nov; some payments."""
    drama, anim = Genre(name="Драма"), Genre(name="Мультфільм")
    old = Title(type=TitleType.MOVIE, title="Хрещений батько", genres=[drama])
    cartoon = Title(type=TitleType.MOVIE, title="Мрія Слонів", genres=[anim, drama])
    series = Title(type=TitleType.SERIES, title="Аркейн", genres=[anim], seasons=[
        Season(number=1, name="С1", episodes=[Episode(number=1, name="Е1"),
                                              Episode(number=2, name="Е2")])])  # fmt: skip
    u1 = User(email="ann@example.com", password_hash="x", display_name="Ann", created_at=at(1, month=10))
    u2 = User(email="bob@example.com", password_hash="x", display_name="Bob", created_at=at(2))
    u3 = User(email="cid@example.com", password_hash="x", display_name="Cid", created_at=at(5, 10))
    free = Plan(code="free", name="Free", price=Decimal(0), period_days=30, max_quality="720p",
                has_ads=True)  # fmt: skip
    premium = Plan(code="premium", name="Premium", price=Decimal(99), period_days=30,
                   max_quality="1080p", has_ads=False)  # fmt: skip
    session.add_all([old, cartoon, series, u1, u2, u3, free, premium])
    session.flush()

    def video(**owner) -> VideoAsset:  # noqa: ANN003
        return VideoAsset(**owner, hls_path="v.m3u8", qualities=["720p"], duration_sec=3600)

    episodes = series.seasons[0].episodes
    v_old, v_cartoon = video(title_id=old.id), video(title_id=cartoon.id)
    v_e1, v_e2 = video(episode_id=episodes[0].id), video(episode_id=episodes[1].id)
    session.add_all([v_old, v_cartoon, v_e1, v_e2])
    session.flush()

    def watch(user, asset, sec, done, moment):  # noqa: ANN001, ANN202
        return WatchHistory(user_id=user.id, video_asset_id=asset.id, progress_sec=sec,
                            completed=done, last_watched_at=moment)  # fmt: skip

    def pay(user, status, moment, plan=premium):  # noqa: ANN001, ANN202
        return Payment(user_id=user.id, plan_id=plan.id, amount=plan.price, provider="mock",
                       scenario=PaymentScenario.SUCCESS, status=status, created_at=moment)  # fmt: skip

    session.add_all([
        watch(u1, v_old, 3600, True, at(2)),
        watch(u2, v_old, 1800, False, at(3)),
        watch(u1, v_e1, 1200, True, at(3, 20)),  # finished, then started over: counts in full
        watch(u1, v_e2, 600, False, at(4)),
        watch(u3, v_cartoon, 900, False, at(5)),
        watch(u2, v_cartoon, 500, False, at(20, month=10)),  # before the period
        pay(u1, PaymentStatus.SUCCEEDED, at(2)),
        pay(u2, PaymentStatus.SUCCEEDED, at(6)),
        pay(u3, PaymentStatus.FAILED, at(5)),
        pay(u2, PaymentStatus.PENDING, at(7)),
        pay(u1, PaymentStatus.SUCCEEDED, at(25, month=10)),  # before the period
        Subscription(user_id=u1.id, plan_id=premium.id, started_at=at(2), expires_at=at(2, month=12)),
        Subscription(user_id=u2.id, plan_id=premium.id, started_at=at(6), expires_at=at(6, month=12)),
    ])  # fmt: skip
    session.commit()
    return {"users": (u1, u2, u3)}


def build(session: Session, code: str) -> ReportResult:
    return ReportService(ReportRepository(session), clock=lambda: NOW).build(code, *WEEK)


def metrics(result: ReportResult) -> dict[str, float]:
    return {m.key: m.value for m in result.metrics}


def chart(result: ReportResult, key: str) -> list[dict]:
    return next(c for c in result.charts if c.key == key).data


# --- Template Method ---------------------------------------------------------------


class RecordingReport(BaseReport[list[str], int]):
    code, title, description = "fake", "Fake", "For tests"

    def __init__(self) -> None:
        super().__init__(repository=None, clock=lambda: NOW)  # type: ignore[arg-type]
        self.calls: list[str] = []

    def collect(self, period: ReportPeriod) -> list[str]:
        self.calls.append("collect")
        return ["a", "b"]

    def aggregate(self, raw: list[str], period: ReportPeriod) -> int:
        self.calls.append("aggregate")
        return len(raw)

    def format(self, data: int, period: ReportPeriod) -> ReportBody:
        self.calls.append("format")
        return ReportBody([Metric("count", "Count", data)], charts=[])


def test_template_method_runs_the_steps_in_order_and_wraps_the_result() -> None:
    report = RecordingReport()
    result = report.build(ReportPeriod(*WEEK))

    assert report.calls == ["collect", "aggregate", "format"]
    assert (result.code, result.generated_at, result.notes) == ("fake", NOW, [])  # default hook
    assert metrics(result) == {"count": 2}


def test_concrete_reports_only_fill_in_the_steps() -> None:
    assert {r.code for r in REPORTS} == {"popularity", "activity", "revenue"}
    for report in REPORTS:
        assert issubclass(report, BaseReport)
        assert report.build is BaseReport.build  # the template itself is not overridden


def test_period_bounds_and_days() -> None:
    period = ReportPeriod(*WEEK)
    assert (period.start_at, period.end_at) == (at(1, 0), at(8, 0))
    assert len(period.days()) == 7


# --- reports -----------------------------------------------------------------------


def test_popularity_report_ranks_titles_and_genres(session: Session, world: dict) -> None:
    result = build(session, "popularity")

    assert metrics(result) == {"views": 4, "viewers": 3, "completions": 2, "titles": 3,
                               "hours": hours(10500)}  # fmt: skip
    assert [(r["title"], r["views"], r["completions"]) for r in result.table.rows] == [
        ("Хрещений батько", 2, 1), ("Аркейн", 1, 1), ("Мрія Слонів", 1, 0)]  # fmt: skip
    assert chart(result, "top_genres") == [{"genre": "Драма", "views": 3},
                                           {"genre": "Мультфільм", "views": 2}]  # fmt: skip
    assert chart(result, "by_type") == [{"type": "Фільми", "views": 3},
                                        {"type": "Серіали", "views": 1}]  # fmt: skip
    assert result.notes  # the hook is used


def test_activity_report_counts_days_and_users(session: Session, world: dict) -> None:
    result = build(session, "activity")

    assert metrics(result) == {
        "users_total": 3, "new_users": 2, "active_users": 3, "hours": hours(10500),
        "hours_per_user": hours(3500), "completions": 2,
    }  # fmt: skip
    daily = {row["day"]: (row["active"], row["new_users"]) for row in chart(result, "daily_users")}
    assert len(daily) == 7
    assert daily["2026-11-02"] == (1, 1)
    assert daily["2026-11-03"] == (2, 0)
    assert daily["2026-11-05"] == (1, 1)
    assert daily["2026-11-07"] == (0, 0)
    top = result.table.rows[0]
    assert (top["email"], top["titles"], top["hours"]) == ("ann@example.com", 2, hours(7800))


def test_revenue_report_sums_successful_payments(session: Session, world: dict) -> None:
    result = build(session, "revenue")

    assert metrics(result) == {
        "revenue": 198.0, "payments": 2, "paying_users": 2, "arppu": 99.0,
        "success_rate": 66.7, "active_subscriptions": 2,
    }  # fmt: skip
    revenue = {row["day"]: row["revenue"] for row in chart(result, "daily_revenue")}
    assert (revenue["2026-11-02"], revenue["2026-11-06"], revenue["2026-11-05"]) == (99, 99, 0)
    assert chart(result, "statuses") == [{"status": "Успішні", "count": 2},
                                         {"status": "Очікують", "count": 1},
                                         {"status": "Відхилені", "count": 1}]  # fmt: skip
    assert result.table.rows == [{"plan": "Premium", "payments": 2, "revenue": 198.0,
                                  "share": 100.0, "active": 2}]  # fmt: skip
    assert any("очікують" in note for note in result.notes)


def test_reports_of_an_empty_database(session: Session) -> None:
    for report in REPORTS:
        result = build(session, report.code)
        assert all(m.value == 0 for m in result.metrics)


def test_service_validates_code_and_period(session: Session) -> None:
    service = ReportService(ReportRepository(session), clock=lambda: NOW)

    default = service.period(None, None)
    assert (default.start, default.end) == (date(2026, 10, 10), date(2026, 11, 8))
    with pytest.raises(UnknownReportError):
        service.build("nope")
    with pytest.raises(InvalidPeriodError):
        service.period(date(2026, 11, 8), date(2026, 11, 1))
    with pytest.raises(InvalidPeriodError):
        service.period(date(2024, 1, 1), date(2026, 1, 1))


# --- API ---------------------------------------------------------------------------


def login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register",
                json={"email": email, "password": "report-pass-1", "display_name": "Boss"})  # fmt: skip
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "report-pass-1"}
                        ).json()["access_token"]  # fmt: skip
    return {"Authorization": f"Bearer {token}"}


def test_reports_api(client: TestClient, session: Session, world: dict) -> None:
    viewer = login(client, "viewer@example.com")
    assert client.get("/api/v1/admin/reports", headers=viewer).status_code == 403
    assert client.get("/api/v1/admin/reports/revenue").status_code == 401

    admin = login(client, "boss@example.com")
    user = session.scalars(select(User).where(User.email == "boss@example.com")).one()
    user.role = UserRole.ADMIN
    session.commit()

    listed = client.get("/api/v1/admin/reports", headers=admin).json()
    assert [r["code"] for r in listed] == ["popularity", "activity", "revenue"]

    params = {"date_from": "2026-11-01", "date_to": "2026-11-07"}
    body = client.get("/api/v1/admin/reports/revenue", params=params, headers=admin).json()
    assert body["period"] == {"start": "2026-11-01", "end": "2026-11-07"}
    assert body["metrics"][0] == {"key": "revenue", "label": "Дохід", "value": 198.0,
                                  "format": "money"}  # fmt: skip
    assert {c["kind"] for c in body["charts"]} == {"bar", "pie"}

    for code in ("popularity", "activity"):
        assert client.get(f"/api/v1/admin/reports/{code}", headers=admin).status_code == 200
    assert client.get("/api/v1/admin/reports/nope", headers=admin).status_code == 404
    reversed_dates = {"date_from": "2026-11-07", "date_to": "2026-11-01"}
    assert client.get("/api/v1/admin/reports/activity", params=reversed_dates,
                      headers=admin).status_code == 422  # fmt: skip
