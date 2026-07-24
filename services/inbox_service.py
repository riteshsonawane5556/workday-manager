import uuid

from agents.email_node import email_node_agent
from graph.pending_store import pending_store
from models.email_models import (
    DraftReply,
    EmailClassification,
    EmailNodeOutput,
)
from tools.email_tools import fetch_email_body, fetch_thread, list_emails
from utils.graph_utils import clean_email_body


async def run_inbox_triage(limit: int = 10) -> tuple[str, list[str]]:
    emails = await list_emails(limit)
    pending_ids: list[str] = []
    processed = 0
    actionable = 0

    for email in emails:
        if await pending_store.has_email(email.id):
            continue
        if await pending_store.is_sent(email.id):
            continue

        try:
            body = clean_email_body(await fetch_email_body(email.id))
        except Exception:
            continue

        thread_section = ""
        if email.thread_id:
            try:
                thread_msgs = await fetch_thread(email.thread_id)
                if len(thread_msgs) > 1:
                    prior = [
                        m for m in thread_msgs if m["id"] != email.id
                    ]
                    if prior:
                        lines = ["THREAD SO FAR:"]
                        for m in prior[-5:]:
                            lines.append(f"[{m['date']}] {m['sender']}: {m['body'][:500]}")
                        thread_section = "\n".join(lines) + "\n\n"
            except Exception:
                pass

        prompt = (
            f"{thread_section}"
            f"Email ID: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\nBody:\n{body}"
        )

        try:
            result = await email_node_agent.run(prompt)
        except Exception:
            continue

        output = result.output
        output.email_id = email.id
        output.subject = email.subject
        output.sender = email.sender
        if output.draft is not None:
            output.draft.to = email.sender

        processed += 1
        if output.classification.label == "actionable" and output.draft is not None:
            pid = await pending_store.add(output)
            pending_ids.append(pid)
            actionable += 1

    lines = [f"Processed {processed} emails. Actionable: {actionable}."]
    if pending_ids:
        lines.append(f"{actionable} draft(s) ready in Pending Approvals.")
    return " ".join(lines), pending_ids


async def stage_outbound_draft(to: str, subject: str, body: str) -> str:
    draft = DraftReply(to=to, subject=subject, body=body)
    output = EmailNodeOutput(
        email_id="",
        subject=subject,
        sender="",
        classification=EmailClassification(
            label="actionable",
            reasoning="User-requested outbound email.",
        ),
        draft=draft,
    )
    return await pending_store.add(output)
