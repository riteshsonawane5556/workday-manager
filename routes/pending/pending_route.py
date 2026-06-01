from fastapi import APIRouter, HTTPException
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from graph.pending_store import pending_store
from agents.send_agent import send_agent
from models.email_models import PendingItem
from tools.email_tools import mark_email_read

router = APIRouter(prefix="/pending", tags=["pending"])


@router.get("", response_model=list[PendingItem])
async def list_pending():
    return pending_store.list_all()


@router.post("/{item_id}/approve")
async def approve_pending(item_id: str):
    item = pending_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pending item not found")

    first_run = await send_agent.run(
        f"Send this email — subject: '{item.draft.subject}', to: '{item.draft.to}', body: '{item.draft.body}'",
        output_type=[DeferredToolRequests, str],
    )

    deferred: DeferredToolRequests = first_run.output
    results: DeferredToolResults = deferred.build_results(approve_all=True)

    await send_agent.run(
        None,
        message_history=first_run.all_messages(),
        deferred_tool_results=results,
        output_type=[DeferredToolRequests, str],
    )

    pending_store.remove(item_id)
    await mark_email_read(item.email_id)
    return {"status": "sent", "id": item_id}


@router.post("/{item_id}/reject")
async def reject_pending(item_id: str):
    if not pending_store.remove(item_id):
        raise HTTPException(status_code=404, detail="Pending item not found")
    return {"status": "rejected", "id": item_id}
