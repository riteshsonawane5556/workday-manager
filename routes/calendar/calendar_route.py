from fastapi import APIRouter, HTTPException

from graph.calendar_graph import run_calendar_pipeline
from models.calendar_models import CalendarAnalysisResult

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/analyze", response_model=CalendarAnalysisResult)
async def analyze_calendar():
    try:
        return await run_calendar_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
