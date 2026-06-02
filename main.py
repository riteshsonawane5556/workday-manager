from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from models.email_models import ChatRequest, ProcessingResult
from routes.auth.auth_route import router as auth_router
from routes.calendar.calendar_route import router as calendar_router
from routes.pending.pending_route import router as pending_router
from graph.email_graph import run_email_pipeline

app = FastAPI(title="Workday Manager", version="0.1.0")

app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(pending_router)


@app.get("/health")
async def health():
    try:
        from config.nylas_client import nylas, NYLAS_GRANT_ID  # noqa: F401
        nylas_status = "connected"
    except Exception:
        nylas_status = "error"
    return {"status": "ok", "nylas": nylas_status}


@app.post("/chat", response_model=ProcessingResult)
async def chat(request: ChatRequest):
    try:
        return await run_email_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
