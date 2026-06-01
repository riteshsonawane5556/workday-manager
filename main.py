from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from models.email_models import ChatRequest, ChatResponse
from agents.email_agent import email_agent
from routes.auth.auth_route import router as auth_router

app = FastAPI(title="Workday Manager", version="0.1.0")

app.include_router(auth_router)


@app.get("/health")
async def health():
    try:
        from config.nylas_client import nylas, NYLAS_GRANT_ID  # noqa: F401
        nylas_status = "connected"
    except Exception:
        nylas_status = "error"
    return {"status": "ok", "nylas": nylas_status}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await email_agent.run(request.message)
        return ChatResponse(reply=result.output)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
