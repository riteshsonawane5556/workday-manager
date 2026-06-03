import re
import warnings
from dataclasses import dataclass, field

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from agents.email_node import email_node_agent
from graph.pending_store import pending_store
from models.email_models import EmailMeta, EmailNodeOutput, ProcessingResult
from tools.email_tools import fetch_email_body, list_emails
from config.logger import get_logger

log = get_logger("email_graph")

_BODY_CHAR_LIMIT = 2000


def _clean_body(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_BODY_CHAR_LIMIT]


@dataclass
class EmailPipelineState:
    emails: list[EmailMeta] = field(default_factory=list)
    current_index: int = 0
    outputs: list[EmailNodeOutput] = field(default_factory=list)
    pending_ids: list[str] = field(default_factory=list)


@dataclass
class FetchEmailsNode(BaseNode[EmailPipelineState]):
    n: int = 10

    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "ClassifyNode":
        log.info("FetchEmailsNode  →  fetching up to %d emails", self.n)
        ctx.state.emails = await list_emails(self.n)
        ctx.state.current_index = 0
        log.info("FetchEmailsNode  →  fetched %d emails", len(ctx.state.emails))
        return ClassifyNode()


@dataclass
class ClassifyNode(BaseNode[EmailPipelineState]):
    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "DraftNode | End[ProcessingResult]":
        idx = ctx.state.current_index
        total = len(ctx.state.emails)

        if idx >= total:
            log.info(
                "ClassifyNode  →  all %d emails processed → END  (actionable=%d)",
                total, len(ctx.state.pending_ids),
            )
            return End(
                ProcessingResult(
                    processed=total,
                    actionable=len(ctx.state.pending_ids),
                    pending_ids=ctx.state.pending_ids,
                )
            )

        email = ctx.state.emails[idx]
        log.info("ClassifyNode  →  [%d/%d] subject=%r  from=%r", idx + 1, total, email.subject, email.sender)

        if pending_store.has_email(email.id):
            log.debug("ClassifyNode  →  email %r already in pending store, skipping", email.id)
            ctx.state.current_index += 1
            return ClassifyNode()

        log.debug("ClassifyNode  →  fetching body for email %r", email.id)
        body = _clean_body(await fetch_email_body(email.id))
        log.debug("ClassifyNode  →  running email_node_agent")
        result = await email_node_agent.run(
            f"Email ID: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\nBody:\n{body}"
        )
        output = result.output
        output.email_id = email.id
        output.subject = email.subject
        output.sender = email.sender
        if output.draft is not None:
            output.draft.to = email.sender
        ctx.state.outputs.append(output)
        log.info(
            "ClassifyNode  →  classified as %r  (draft=%s)",
            output.classification.label, output.draft is not None,
        )
        return DraftNode()


@dataclass
class DraftNode(BaseNode[EmailPipelineState]):
    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "HumanGateNode | ClassifyNode":
        output = ctx.state.outputs[-1]
        if output.classification.label == "actionable" and output.draft is not None:
            log.info("DraftNode  →  email is actionable with draft → routing to HumanGateNode")
            return HumanGateNode()
        log.debug("DraftNode  →  not actionable or no draft, moving to next email")
        ctx.state.current_index += 1
        return ClassifyNode()


@dataclass
class HumanGateNode(BaseNode[EmailPipelineState]):
    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "ClassifyNode":
        output = ctx.state.outputs[-1]
        pending_id = pending_store.add(output)
        ctx.state.pending_ids.append(pending_id)
        log.info("HumanGateNode  →  stored pending draft  id=%r  subject=%r", pending_id, output.subject)
        ctx.state.current_index += 1
        return ClassifyNode()


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    email_graph = Graph(
        nodes=(FetchEmailsNode, ClassifyNode, DraftNode, HumanGateNode),
        state_type=EmailPipelineState,
    )


async def run_email_pipeline(n: int = 10) -> ProcessingResult:
    log.info("=== Email pipeline START ===")
    state = EmailPipelineState()
    result = await email_graph.run(FetchEmailsNode(n=n), state=state)
    log.info("=== Email pipeline END ===")
    return result.output
