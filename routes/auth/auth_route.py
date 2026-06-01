from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
async def auth_status():
    """Placeholder for Nylas hosted OAuth flow in later phases."""
    return {"status": "not_implemented", "phase": 1}
