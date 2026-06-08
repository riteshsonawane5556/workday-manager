from fastapi import APIRouter, HTTPException
from graph.pending_store import pending_store
from models.email_models import PendingItem
from services.pending_service import send_approved_email

router = APIRouter(prefix="/pending", tags=["pending"])


@router.get("", response_model=list[PendingItem])
async def list_pending():
    return await pending_store.list_all()


@router.post("/{item_id}/approve")
async def approve_pending(item_id: str):
    item = await pending_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pending item not found")

    await send_approved_email(item)

    await pending_store.remove(item_id)
    return {"status": "sent", "id": item_id}


@router.post("/{item_id}/reject")
async def reject_pending(item_id: str):
    if not await pending_store.remove(item_id):
        raise HTTPException(status_code=404, detail="Pending item not found")
    return {"status": "rejected", "id": item_id}
