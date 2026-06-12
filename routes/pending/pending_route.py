from fastapi import APIRouter, HTTPException

from models.email_models import DraftReply, PendingItem
from services.pending_service import (
    get_pending_item,
    list_pending_items,
    remove_pending_item,
    send_approved_email,
    update_pending_draft,
)

router = APIRouter(prefix="/pending", tags=["pending"])


@router.get("", response_model=list[PendingItem])
async def list_pending():
    return await list_pending_items()


@router.post("/{item_id}/approve")
async def approve_pending(item_id: str):
    item = await get_pending_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pending item not found")

    await send_approved_email(item)
    await remove_pending_item(item_id)
    return {"status": "sent", "id": item_id}


@router.patch("/{item_id}/draft")
async def edit_pending_draft(item_id: str, draft: DraftReply):
    updated = await update_pending_draft(item_id, draft)
    if not updated:
        raise HTTPException(status_code=404, detail="Pending item not found")
    return {"status": "updated", "id": item_id}


@router.post("/{item_id}/reject")
async def reject_pending(item_id: str):
    if not await remove_pending_item(item_id):
        raise HTTPException(status_code=404, detail="Pending item not found")
    return {"status": "rejected", "id": item_id}
