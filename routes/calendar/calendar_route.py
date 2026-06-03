from fastapi import APIRouter, HTTPException

from graph.planner_graph import run_orchestrator_pipeline
from models.calendar_models import CalendarAnalysisResult

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/analyze", response_model=CalendarAnalysisResult)
async def analyze_calendar():
    try:
        result = await run_orchestrator_pipeline("analyze my calendar for today")
        if result.calendar_result is None:
            raise HTTPException(status_code=500, detail="Calendar analysis failed")
        return result.calendar_result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
