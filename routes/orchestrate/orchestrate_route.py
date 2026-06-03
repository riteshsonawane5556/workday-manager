from fastapi import APIRouter, HTTPException

from graph.planner_graph import run_orchestrator_pipeline
from models.orchestrator_models import OrchestratorRequest, OrchestratorResult

router = APIRouter(prefix="/orchestrate", tags=["orchestrate"])


@router.post("", response_model=OrchestratorResult)
async def orchestrate(request: OrchestratorRequest):
    try:
        return await run_orchestrator_pipeline(request.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
