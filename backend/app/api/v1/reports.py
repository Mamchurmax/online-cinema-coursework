"""Admin reports (Template Method): popularity, user activity, revenue."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AdminUser, DbSession
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportInfo, ReportRead
from app.services.reports.report_service import (
    InvalidPeriodError,
    ReportService,
    UnknownReportError,
)

router = APIRouter(prefix="/admin/reports", tags=["admin: reports"])


def get_report_service(db: DbSession) -> ReportService:
    return ReportService(ReportRepository(db))


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


@router.get("", response_model=list[ReportInfo])
def list_reports(_: AdminUser, reports: ReportServiceDep):
    return [
        ReportInfo(code=r.code, title=r.title, description=r.description)
        for r in reports.available()
    ]


@router.get("/{code}", response_model=ReportRead)
def build_report(
    code: str,
    _: AdminUser,
    reports: ReportServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Both dates are inclusive (UTC); by default — the last 30 days."""
    try:
        return reports.build(code, date_from, date_to)
    except UnknownReportError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from None
    except InvalidPeriodError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
