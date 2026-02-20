from fastapi import APIRouter

from app.core.deps import ReportsServiceDep
from app.models.report import ReportGenerateRequest, ReportGenerateResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    body: ReportGenerateRequest,
    reports_service: ReportsServiceDep,
) -> ReportGenerateResponse:
    return await reports_service.generate_report(body)
