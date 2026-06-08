from dotenv import load_dotenv

load_dotenv()

import logfire

logfire.configure(
    service_name="workday-manager",
    scrubbing=False,
    inspect_arguments=False,
)
logfire.instrument_pydantic_ai(
    include_content=True,
    version=3,
)

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from models.email_models import ChatRequest
from models.orchestrator_models import OrchestratorResult
from routes.auth.auth_route import router as auth_router
from routes.pending.pending_route import router as pending_router
from routes.orchestrate.orchestrate_route import router as orchestrate_router
from graph.planner_graph import run_orchestrator_pipeline
from config.logger import get_logger

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from config.database import DATABASE_URL
    log.info("Workday Manager starting up  (db=%s)", DATABASE_URL)
    yield
    logfire.force_flush()


app = FastAPI(title="Workday Manager", version="0.1.0", lifespan=lifespan)
logfire.instrument_fastapi(app)

app.include_router(auth_router)
app.include_router(pending_router)
app.include_router(orchestrate_router)


@app.get("/health")
async def health():
    try:
        from config.nylas_client import nylas, NYLAS_GRANT_ID  # noqa: F401
        nylas_status = "connected"
    except Exception:
        nylas_status = "error"
    return {"status": "ok", "nylas": nylas_status}


# @app.post("/chat", response_model=OrchestratorResult)
# async def chat(request: ChatRequest):
#     log.info("POST /chat  ->  starting workday pipeline")
#     try:
#         result = await run_orchestrator_pipeline("check and triage my inbox")
#         log.info("POST /chat  ->  done")
#         return result
#     except Exception as exc:
#         log.error("POST /chat  ->  error: %s", exc, exc_info=True)
#         raise HTTPException(status_code=500, detail=str(exc))
